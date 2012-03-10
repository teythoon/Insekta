import random
import hmac
import hashlib
from datetime import datetime

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User

from insekta.network.models import Address
from insekta.vm.models import VirtualMachine, BaseImage

AVAILABLE_TASKS = {
    'create': 'Create VM',
    'start': 'Start VM',
    'stop': 'Stop VM',
    'suspend': 'Suspend VM',
    'resume': 'Suspend VM',
    'destroy': 'Destroy VM'
}

class ScenarioError(Exception):
    pass

class InvalidSecret(ScenarioError):
    pass

class Scenario(models.Model):
    name = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    num_secrets = models.IntegerField()
    memory = models.IntegerField()
    image = models.ForeignKey(BaseImage)
    enabled = models.BooleanField(default=False)

    class Meta:
        permissions = (
            ('view_editor', _('Can view the scenario editor')),
        )

    def __unicode__(self):
        return self.title

    def get_secrets(self):
        """Return a frozenset of secrets as strings."""
        return frozenset(secret.secret for secret in self.secret_set.all())

    def get_submitted_secrets(self, user):
        """Return a frozenset of user submitted secrets.

        :param user: Instance of :class:`django.contrib.auth.models.User`.
        """
        submitted_secrets = SubmittedSecret.objects.filter(user=user,
                secret__scenario=self)
        return frozenset(sub.secret.secret for sub in submitted_secrets)
    
    def submit_secret(self, user, secret, tokens=None):
        """Submit a secret for a user.

        :param user: Instance of :class:`django.contrib.auth.models.User`.
        :param secret: The secret as string.
        :param tokens: A list of security tokens calculated by the function
                       :func:`insekta.scenario.models.calculate_secret_token`.
                       The secret will only be accepted, if it's token is
                       inside this list.
        :rtype: :class:`insekta.scenario.models.SubmittedSecret`
        """
        try:
            secret_obj = Secret.objects.get(scenario=self, secret=secret)
        except Secret.DoesNotExist:
            raise InvalidSecret(_('This secret is invalid!'))
        else:
            valid_token = calculate_secret_token(user, secret)
            if tokens is not None and valid_token not in tokens:
                raise InvalidSecret(_('This secret is invalid!'))
            
            if secret in self.get_submitted_secrets(user):
                raise InvalidSecret(_('This secret was already submitted!'))
            
            return SubmittedSecret.objects.create(secret=secret_obj, user=user)

    def get_nodes(self):
        """Return a list containing all nodes this scenario can run on."""
        return settings.LIBVIRT_NODES.keys()

    def start(self, user, node=None):
        """Start this scenario for the given user.

        :param user: Instance of :class:`django.contrib.auth.models.User`.
        :rtype: :class:`insekta.scenario.models.ScenarioRun`.
        """
        if not self.enabled:
            raise ScenarioError('Scenario is not enabled')

        if node is None:
            node = random.choice(self.get_nodes())

        vm = VirtualMachine.objects.create(node=node, memory=self.memory,
                base_image=self.image, address=Address.objects.get_free())

        return ScenarioRun.objects.create(vm=vm, user=user, scenario=self)

    def get_run(self, user, fail_silently=False):
        """Return the ScenarioRun for an user if it exists."""
        try:
            return ScenarioRun.objects.get(user=user, scenario=self)
        except ScenarioRun.DoesNotExist:
            if not fail_silently:
                raise

class ScenarioRun(models.Model):
    scenario = models.ForeignKey(Scenario)
    user = models.ForeignKey(User)
    last_activity = models.DateTimeField(default=datetime.today, db_index=True)
    vm = models.OneToOneField(VirtualMachine)

    class Meta:
        unique_together = (('user', 'scenario'), )

    @property
    def expires_at(self):
        return self.last_activity + settings.SCENARIO_EXPIRE_TIME
    
    def heartbeat(self):
        self.last_activity = datetime.today()
        self.save()

    def __unicode__(self):
        return u'{0} running "{1}"'.format(self.user, self.scenario)

class RunTaskQueue(models.Model):
    scenario_run = models.ForeignKey(ScenarioRun, unique=True)
    action = models.CharField(max_length=10, choices=AVAILABLE_TASKS.items())

    def __unicode__(self):
        return u'{0} for {1}'.format(self.get_action_display(),
                                     unicode(self.scenario_run))

class Secret(models.Model):
    scenario = models.ForeignKey(Scenario)
    secret = models.CharField(max_length=40)

    class Meta:
        unique_together = (('scenario', 'secret'), )

    def __unicode__(self):
        return u'{0}.{1}'.format(self.scenario.name, self.secret)

class SubmittedSecret(models.Model):
    secret = models.ForeignKey(Secret)
    user = models.ForeignKey(User)

    class Meta:
        unique_together = (('user', 'secret'), )

    def __unicode__(self):
        return u'{0} submitted secret "{1}"'.format(self.user, self.secret)

class ScenarioGroup(models.Model):
    title = models.CharField(max_length=200)
    scenarios = models.ManyToManyField(Scenario, related_name='groups',
                                       through='ScenarioBelonging')

    def __unicode__(self):
        return self.title

class ScenarioBelonging(models.Model):
    scenario = models.ForeignKey(Scenario)
    scenario_group = models.ForeignKey(ScenarioGroup)
    rank = models.IntegerField()

    class Meta:
        unique_together = (('scenario', 'scenario_group'), )

    def __unicode__(self):
        return u'{0} belongs to group {1} with rank {2}'.format(unicode(
                self.scenario), unicode(self.scenario_group), self.rank)

class UserProgress(models.Model):
    user = models.ForeignKey(User, db_index=True)
    scenario = models.ForeignKey(Scenario)
    num_secrets = models.IntegerField(default=0)

    def __unicode__(self):
        return u'{0} submitted {1} secrets for {1}'.format(self.user,
                self.num_secrets, self.scenario)

def calculate_secret_token(user, secret):
    msg = '{0}:{1}'.format(user.pk, secret)
    hmac_gen = hmac.new(settings.SECRET_KEY, msg, hashlib.sha1)
    return hmac_gen.hexdigest()

def _update_progress(sender, instance, **kwargs):
    scenario = instance.secret.scenario
    num_secrets = SubmittedSecret.objects.filter(user=instance.user,
            secret__scenario=scenario).aggregate(c=models.Count('secret'))['c']
    progress, _created = UserProgress.objects.get_or_create(user=instance.user,
            scenario=scenario)
    progress.num_secrets = num_secrets
    progress.save()

post_save.connect(_update_progress, SubmittedSecret)
post_delete.connect(_update_progress, SubmittedSecret)

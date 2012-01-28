import random
import hmac
import hashlib

import libvirt
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User

from insekta.common.virt import connections
from insekta.network.models import Address

HYPERVISOR_CHOICES = (
    ('qemu', 'Qemu (with KVM)'),
)

RUN_STATE_CHOICES = (
    ('disabled', 'VM is not created yet'),
    ('preparing', 'Preparing'),
    ('started', 'VM started'),
    ('suspended', 'VM suspended'),
    ('stopped', 'VM stopped'),
    ('error', 'VM has weird error')
)

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
    memory = models.IntegerField()
    hypervisor = models.CharField(max_length=10, default='qemu',
                                  choices=HYPERVISOR_CHOICES)
    description = models.TextField()
    num_secrets = models.IntegerField()
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
        # For now, we have only one node per hypervisor, but this
        # can change. Using this method we can easily assign
        # each scenario an own node or several nodes if we need
        # to scale.
        return [self.hypervisor]

    def get_pool(self, node):
        """Return the pool where volume of the scenario image is stored.
        
        :param node: A libvirt node, e.g. 'mynode'
        :rtype: :class:`libvirt.virStoragePool`
        """
        pool_name = settings.LIBVIRT_STORAGE_POOLS[node]
        return connections[node].storagePoolLookupByName(pool_name)

    def get_volume(self, node):
        """Return the volume where the image of this scenario is stored.

        :param node: A libvirt node, e.g. 'mynode'.
        :rtype: :class:`libvirt.virStorageVol`

        >>> scenario = Scenario.objects.get(pk=1)
        >>> vol = scenario.get_volume('mynode')
        >>> print(vol.path()) # Prints /dev/insekta/simple-buffer-overflow
        """
        pool = self.get_pool(node)
        return pool.storageVolLookupByName(self.name)

    def start(self, user, node=None):
        """Start this scenario for the given user.

        :param user: Instance of :class:`django.contrib.auth.models.User`.
        :rtype: :class:`insekta.scenario.models.ScenarioRun`.
        """
        if not self.enabled:
            raise ScenarioError('Scenario is not enabled')

        if node is None:
            node = random.choice(self.get_nodes())

        return ScenarioRun.objects.create(scenario=self, user=user, node=node,
                                          address=Address.objects.get_free())

class ScenarioRun(models.Model):
    scenario = models.ForeignKey(Scenario)
    user = models.ForeignKey(User)
    node = models.CharField(max_length=20)
    address = models.ForeignKey(Address)
    state = models.CharField(max_length=10, default='disabled',
                             choices=RUN_STATE_CHOICES)

    class Meta:
        unique_together = (('user', 'scenario'), )

    def start(self):
        """Start the virtual machine."""
        self._do_vm_action('create', 'started')

    def stop(self):
        """Stops the virtual machine."""
        self._do_vm_action('destroy', 'stopped')

    def suspend(self):
        """Suspends the virtual machine."""
        self._do_vm_action('suspend', 'suspended')

    def resume(self):
        self._do_vm_action('resume', 'started')

    def refresh_state(self):
        """Fetches the state from libvirt and saves it."""
        try:
            domain = self.get_domain()
        except libvirt.libvirtError:
            self.state = 'disabled'
        else:
            try:
                state, _reason = domain.state(flags=0)
            except libvirt.libvirtError:
                new_state = 'error'
            else:
                new_state = {
                    libvirt.VIR_DOMAIN_NOSTATE: 'error',
                    libvirt.VIR_DOMAIN_RUNNING: 'started',
                    libvirt.VIR_DOMAIN_BLOCKED: 'error',
                    libvirt.VIR_DOMAIN_PAUSED: 'suspended',
                    libvirt.VIR_DOMAIN_SHUTDOWN: 'error',
                    libvirt.VIR_DOMAIN_SHUTOFF: 'stopped'
                }.get(state, 'error')
            self.state = new_state

    def create_domain(self):
        """Create a domain for this scenario run.

        This includes the following:
        * Cloning the volume of the scenario
        * Creating a new domain using the cloned volume as disk
        * Starting the domain

        :rtype: :class:`libvirt.virDomain`.
        """
        volume = self._create_volume()
        xml_desc = self._build_domain_xml(volume)
        domain = connections[self.node].defineXML(xml_desc)
        self.state = 'stopped'
        self.save()
        return domain

    def destroy_domain(self):
        """ Destroy a domain of this scenario run.

        This includes the following:
        * Killing the domain if it is running
        * Undefining the domain
        * Deleting the volume of the domain
        """
        try:
            self._do_vm_action('destroy', 'stopped')
        except ScenarioError:
            # It is already stopped, just ignore exception
            pass
        self._do_vm_action('undefine', 'disabled')
        self.get_volume().delete(flags=0)

    def get_domain(self):
        """Return the domain of this scenario run.

        :rtype: :class:`libvirt.virDomain`.
        """
        conn = connections[self.node]
        return conn.lookupByName('scenarioRun{0}'.format(self.pk))

    def get_volume(self):
        """Return the volume where this scenario run stores it's data.

        :rtype: :class:`libvirt.virStorageVol`.
        """
        pool = self.scenario.get_pool(self.node)
        return pool.storageVolLookupByName('scenarioRun{0}'.format(self.pk))

    def _create_volume(self):
        """Create a new volume by using a backing image.

        :rtype: :class:`libvirt.virStorageVol`
        """
        pool = self.scenario.get_pool(self.node)
        base_volume = self.scenario.get_volume(self.node)
        capacity = base_volume.info()[1]
        xmldesc = """
        <volume>
          <name>scenarioRun{id}</name>
          <capacity>{capacity}</capacity>
          <target>
            <format type='qcow2' />
          </target>
          <backingStore>
            <path>{backing_image}</path>
            <format type='qcow2' />
          </backingStore>
        </volume>
        """.format(id=self.pk, capacity=capacity,
                   backing_image=base_volume.path())
        return pool.createXML(xmldesc, flags=0)
    
    def _build_domain_xml(self, volume):
        scenario = self.scenario
        return """
        <domain type='kvm'>
          <name>scenarioRun{id}</name>
          <description>{user} running &quot;{title}&quot;</description>
          <memory>{memory}</memory>
          <vcpu>1</vcpu>
          <os>
            <type arch="x86_64">hvm</type>
          </os>
          <devices>
            <disk type='file' device='disk'>
              <driver name='qemu' type='qcow2' />
              <source file='{volume}' />
              <target dev='vda' bus='virtio' />
            </disk>
            <interface type='bridge'>
              <mac address='{mac}' />
              <source bridge='{bridge}' />
              <model type='virtio' />
            </interface>
            <graphics type='vnc' port='-1' autoport='yes' />
          </devices>
        </domain>
        """.format(id=self.pk, user=self.user.username, title=scenario.title,
                   memory=scenario.memory * 1024, volume=volume.path(),
                   mac=self.address.mac, bridge=settings.VM_BRIDGE)
    
    def _do_vm_action(self, action, new_state):
        """Do an action on the virtual machine.

        After executing the action, the scenario run is in the state
        `new_state`.
        
        If it fails, it will reread the state from libvirt, since this is
        mostly the cause for failing.

        :param action: One of 'start', 'destroy', 'suspend', 'resume' and
                       'undefine'
        """
        try:
            domain = self.get_domain()
            getattr(domain, action)()
            self.state = new_state
        except libvirt.libvirtError, e:
            self.refresh_state()
            raise ScenarioError(str(e))
        finally:
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

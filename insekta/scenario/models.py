from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

from insekta.common.virt import connections

HYPERVISOR_CHOICES = (
    ('qemu', 'Qemu (with KVM)'),
)

RUN_STATE_CHOICES = (
    ('init', 'Initialize'),
    ('preparing', 'Preparing'),
    ('running', 'Running'),
)

class Scenario(models.Model):
    name = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=200)
    memory = models.IntegerField()
    hypervisor = models.CharField(max_length=10, default='qemu',
                                  choices=HYPERVISOR_CHOICES)
    description = models.TextField()
    enabled = models.BooleanField(default=False)

    def __unicode__(self):
        return self.title

    def get_nodes(self):
        # For now, we have only one node per hypervisor, but this
        # can change. Using this method we can easily assign
        # each scenario an own node or several nodes if we need
        # to scale.
        return [self.hypervisor]

    def get_volume(self, node):
        """Return the volume where the image of this scenario is stored.

        :param node: A libvirt node e.g. 'mynode'.
        :return: :class:`libvirt.virStorageVol`

        >>> scenario = Scenario.objects.get(pk=1)
        >>> vol = scenario.get_volume('mynode')
        >>> print(vol.path()) # Prints /dev/insekta/simple-buffer-overflow
        """
        pool_name = settings.LIBVIRT_STORAGE_POOLS[node]
        pool = connections[node].storagePoolLookupByName(pool_name)
        return pool.storageVolLookupByName(self.name)

    def start(self, user):
        return ScenarioRun.objects.create(scenario=self, user=user)

class ScenarioRun(models.Model):
    scenario = models.ForeignKey(Scenario)
    user = models.ForeignKey(User)
    state = models.CharField(max_length=10, default='init',
                             choices=RUN_STATE_CHOICES)
    
    def build_domain_xml(self):
        return """
        <domain>
          <name>{name}</name>
          <description>{title}</description>
          <memory>{mem}</memory>
          <vcpu>1</vcpu>
          <os>
            <type arch="x86_64">hvm</type>
          </os>
          <devices>
            <disk type='file' device='disk'>
              <source file='/tmp/foo.img' />
              <target dev='hda' />
            </disk>
            <interface type='bridge'>
              <source bridge='br0' />
            </interface>'
            <graphics type='vnc' port='-1' autoport='yes' />
          </devices>
        </domain>
        """.format(name=self.name, title=self.title, mem=self.memory * 1024)

    def __unicode__(self):
        return u'{} running "{}"'.format(self.user, self.scenario)

class Secret(models.Model):
    scenario = models.ForeignKey(Scenario)
    secret = models.CharField(max_length=40)

    class Meta:
        unique_together = (('scenario', 'secret'), )

    def __unicode__(self):
        return self.secret

class SubmittedSecret(models.Model):
    secret = models.ForeignKey(Secret)
    user = models.ForeignKey(User)

    def __unicode__(self):
        return u'{} submitted secret "{}"'.format(self.user, self.secret)

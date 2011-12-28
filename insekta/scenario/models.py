import random

import libvirt
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

class ScenarioError(Exception):
    pass

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
        """Return a list containing all nodes this scenario can run on."""
        # For now, we have only one node per hypervisor, but this
        # can change. Using this method we can easily assign
        # each scenario an own node or several nodes if we need
        # to scale.
        return [self.hypervisor]

    def get_pool(self, node):
        """Return the pool where volume of the scenario image is stored.
        
        :param node: A libvirt node, e.g. 'mynode'
        :return: :class:`libvirt.virStoragePool`
        """
        pool_name = settings.LIBVIRT_STORAGE_POOLS[node]
        return connections[node].storagePoolLookupByName(pool_name)

    def get_volume(self, node):
        """Return the volume where the image of this scenario is stored.

        :param node: A libvirt node, e.g. 'mynode'.
        :return: :class:`libvirt.virStorageVol`

        >>> scenario = Scenario.objects.get(pk=1)
        >>> vol = scenario.get_volume('mynode')
        >>> print(vol.path()) # Prints /dev/insekta/simple-buffer-overflow
        """
        pool = self.get_pool(node)
        return pool.storageVolLookupByName(self.name)

    def start(self, user, node=None):
        """Start this scenario for the given user.

        :param user: Instance of :class:`django.contrib.auth.models.User`.
        :return: Instance of :class:`insekta.scenario.models.ScenarioRun`.
        """
        if not self.enabled:
            raise ScenarioError('Scenario is not enabled')

        if node is None:
            node = random.choice(self.get_nodes())
        return ScenarioRun.objects.create(scenario=self, user=user)

class ScenarioRun(models.Model):
    scenario = models.ForeignKey(Scenario)
    user = models.ForeignKey(User)
    node = models.CharField(max_length=20)
    state = models.CharField(max_length=10, default='init',
                             choices=RUN_STATE_CHOICES)

    def create_domain(self):
        """Create a domain for this scenario run.

        This includes the following:
        * Cloning the volume of the scenario
        * Creating a new domain using the cloned volume as disk
        * Starting the domain

        :return: Instance of :class:`libvirt.virDomain`.
        """
        volume = self._create_volume()
        xml_desc = self._build_domain_xml(self, volume)
        domain = connections[self.node].defineXML(xml_desc)
        domain.create()
        self.state = 'running'
        return domain

    def destroy_domain(self):
        """ Destroy a domain of this scenario run.

        This includes the following:
        * Killing the domain if it is running
        * Undefining the domain
        * Deleting the volume of the domain
        """
        # FIXME: Protection against race conditions
        domain = self.get_domain()
        try:
            domain.destroy()
        except libvirt.libvirtError:
            # Domain is not running, we can ignore the exception
            pass
        domain.undefine()
        self.get_volume().delete(flags=0)

    def get_domain(self):
        """Return the domain of this scenario run.

        :return: Instance of :class:`libvirt.virDomain`.
        """
        conn = connections[self.node]
        return conn.lookupByName('scenarioRun{}'.format(self.pk))

    def get_volume(self):
        """Return the volume where this scenario run stores it's data.

        :return: Instance of :class:`libvirt.virStorageVol`.
        """
        pool = self.scenario.get_pool(self.node)
        return pool.storageVolLookupByName('scenarioRun{}'.format(self.pk))

    def _create_volume(self):
        """Create a new volume by cloning the scenario volume.

        :return: :class:`libvirt.virStorageVol`
        """
        pool = self.scenario.get_pool(self.node)
        clone_vol = self.scenario.get_volume(self.node)
        capacity = clone_vol.info()[1]
        xmldesc = """
        <volume>
          <name>scenarioRun{}</name>
          <capacity>{}</capacity>
        </volume>
        """.format(self.pk, capacity)
        return pool.createXMLFrom(xmldesc, clone_vol, flags=0)
    
    def _build_domain_xml(self, volume):
        scenario = self.scenario
        return """
        <domain>
          <name>scenarioRun{id}</name>
          <description>{user} running &quot;{title}&quot;</description>
          <memory>{memory}</memory>
          <vcpu>1</vcpu>
          <os>
            <type arch="x86_64">hvm</type>
          </os>
          <devices>
            <disk type='block' device='disk'>
              <source dev='{volume}' />
              <target dev='hda' />
            </disk>
            <interface type='bridge'>
              <source bridge='br0' />
            </interface>'
            <graphics type='vnc' port='-1' autoport='yes' />
          </devices>
        </domain>
        """.format(id=self.pk, user=self.user.username, title=scenario.title,
                   memory=scenario.memory * 1024, volume=volume.target())


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

class ScenarioGroup(models.Model):
    title = models.CharField(max_length=200)
    scenarios = models.ManyToManyField(Scenario, related_name='groups')

    def __unicode__(self):
        self.title

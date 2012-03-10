from django.db import models
from django.conf import settings
from django.template.loader import render_to_string
import libvirt

from insekta.common.virt import connections
from insekta.network.models import Address

RUN_STATE_CHOICES = (
    ('disabled', 'VM is not created yet'),
    ('preparing', 'Preparing'),
    ('started', 'VM started'),
    ('suspended', 'VM suspended'),
    ('stopped', 'VM stopped'),
    ('error', 'VM has weird error')
)

class VirtualMachineError(Exception):
    pass

class BaseImage(models.Model):
    name = models.CharField(max_length=80)
    hash = models.CharField(max_length=40)
    
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

    def __unicode__(self):
        return self.name

class VirtualMachine(models.Model):
    memory = models.IntegerField()
    base_image = models.ForeignKey(BaseImage)
    node = models.CharField(max_length=80)
    address = models.OneToOneField(Address)
    state = models.CharField(max_length=10, default='disabled',
                             choices=RUN_STATE_CHOICES)

    def start(self):
        """Start the virtual machine."""
        self._do_vm_action('create', 'started')

    def stop(self):
        """Stop the virtual machine."""
        self._do_vm_action('destroy', 'stopped')

    def suspend(self):
        """Suspend the virtual machine."""
        self._do_vm_action('suspend', 'suspended')

    def resume(self):
        """Resume the virtual machine."""
        self._do_vm_action('resume', 'started')

    def destroy(self):
        """Destroy this scenario run including virtual machine."""
        try:
            self.stop()
        except VirtualMachineError:
            pass
        self.destroy_domain()
        self.delete()

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
        except VirtualMachineError:
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
        pool = self.base_image.get_pool(self.node)
        return pool.storageVolLookupByName('scenarioRun{0}'.format(self.pk))

    def _create_volume(self):
        """Create a new volume by using a backing image.

        :rtype: :class:`libvirt.virStorageVol`
        """
        pool = self.base_image.get_pool(self.node)
        base_volume = self.base_image.get_volume(self.node)
        capacity = base_volume.info()[1]
        xmldesc = render_to_string('vm/volume.xml', {
            'id': self.pk,
            'capacity': capacity,
            'backing_image': base_volume.path()
        })
        return pool.createXML(xmldesc, flags=0)
    
    def _build_domain_xml(self, volume):
        return render_to_string('vm/domain.xml', {
            'id': self.pk,
            'user': self.user,
            'memory': self.memory * 1024,
            'volume': volume.path(),
            'mac': self.address.mac,
            'bridge': settings.VM_BRIDGE
        })
    
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
            raise VirtualMachineError(unicode(e))
        finally:
            self.save()


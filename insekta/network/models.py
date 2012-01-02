import random

from django.db import models, transaction, IntegrityError
from django.conf import settings

from insekta.common.dblock import dblock
from insekta.network.utils import iterate_ips

LOCK_NETWORK_ADDRESS = 947295

class NetworkError(Exception):
    pass

class AddressManager(models.Manager):
    def get_free(self):
        """Get a free address and mark it as in use."""
        try:
            with dblock(LOCK_NETWORK_ADDRESS):
                address = self.get_query_set().filter(in_use=False)[0]
                address.take_address()
                return address
        except IndexError:
            raise NetworkError('No more free addresses.')

    @transaction.commit_manually
    def fill_pool(self):
        """Insert all addresses into the pool."""
        def random_16():
            return ''.join(random.choice('0123456789abcdef') for _i in (0, 1))

        new_addresses = []
        oui = getattr(settings, 'VM_MAC_OUI', '52:54:00')
        try:
            ip_blocks = settings.VM_IP_BLOCKS
        except AttributeError:
            raise NetworkError('Please set VM_IP_BLOCKS in settings.py')
        
        for ip in iterate_ips(ip_blocks):
            mac = ':'.join((oui, random_16(), random_16(), random_16()))
            try:
                new_addresses.append(Address.objects.create(mac=mac, ip=ip))
            except IntegrityError:
                transaction.rollback()
            else:
                transaction.commit()
        return new_addresses


class Address(models.Model):
    ip = models.IPAddressField(unique=True)
    mac = models.CharField(max_length=17, unique=True)
    in_use = models.BooleanField(default=False)

    objects = AddressManager()

    def __unicode__(self):
        return '{0} with IP {1}'.format(self.mac, self.ip)

    def take_address(self):
        self.in_use = True
        self.save()

    def return_address(self):
        self.in_use = False
        self.save()

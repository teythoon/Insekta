import random

from django.db import models, transaction, IntegrityError
from django.conf import settings

from insekta.network.utils import get_random_ip

class NetworkError(Exception):
    pass

class AddressManager(models.Manager):
    def get_free(self):
        """Get a free address and mark it as in use."""
        try:
            address = self.get_query_set().filter(in_use=False)[0]
            address.take_address()
            return address
        except IndexError:
            raise NetworkError('No more free addresses.')

    @transaction.commit_manually
    def fill_pool(self, amount=10):
        """Insert `amount` random addresses.

        ..warning:
           Make sure there are enough non-allocated addresses, otherwise this
           method does not terminate!
        """
        def random_16():
            return ''.join(random.choice('0123456789abcdef') for _i in (0, 1))

        new_addresses = []
        oui = getattr(settings, 'VM_MAC_OUI', '52:54:00')
        ip_blocks = getattr(settings, 'VM_IP_BLOCKS', '192.168.0.0/24')
        while amount > 0:
            mac = ':'.join((oui, random_16(), random_16(), random_16()))
            ip = get_random_ip(ip_blocks)
            try:
                new_addresses.append(Address.objects.create(mac=mac, ip=ip))
            except IntegrityError:
                transaction.rollback()
            else:
                transaction.commit()
                amount -= 1
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

from __future__ import print_function

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from insekta.network.models import Address
from insekta.network.utils import ip_to_int, int_to_ip, cidr_to_netmask

class Command(BaseCommand):
    args = '<fill [amount=100] | dump | dhcpconf>'
    help = ('Dumps network database or fill it with random mac addresses '
            'or generate DHCP config host entries for ISC DHCP server ')
           

    def handle(self, *args, **options):
        if not args:
            raise CommandError('What do you want? fill or dump or dhcpconf?')
        
        if args[0] == 'fill':
            addresses = Address.objects.fill_pool()
            for addr in addresses:
                print('{0}={1}'.format(addr.mac, addr.ip))
            print('\nInserted {0} addresses.'.format(len(addresses)))
        elif args[0] == 'dump':
            for addr in Address.objects.all():
                print('{0}\t{1}'.format(addr.mac, addr.ip))
        elif args[0] == 'dhcpconf':
            for addr in Address.objects.all():
                print('host vm{0} {{'.format(addr.pk))
                print('\thardware ethernet {0}'.format(addr.mac))
                print('\tfixed-address {0}'.format(addr.ip))
                subnet_mask = int_to_ip(cidr_to_netmask(settings.VM_NET_SIZE))
                print('\toption subnet-mask {0}'.format(subnet_mask))
                router_ip = int_to_ip(ip_to_int(addr.ip) - 1)
                print('\toption routers {0}'.format(router_ip))
                print('}')

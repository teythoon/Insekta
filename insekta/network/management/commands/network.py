from __future__ import print_function

from django.core.management.base import BaseCommand, CommandError

from insekta.network.models import Address

class Command(BaseCommand):
    args = '<fill [amount=100] | dump>'
    help = 'Dumps network database or fill it with random mac addresses'

    def handle(self, *args, **options):
        if not args:
            raise CommandError('What do you want? fill or dump?')
        
        if args[0] == 'fill':
            addresses = Address.objects.fill_pool()
            for addr in addresses:
                print('{0}={1}'.format(addr.mac, addr.ip))
            print('\nInserted {0} addresses.'.format(len(addresses)))
        elif args[0] == 'dump':
            for addr in Address.objects.all():
                print('{0}\t{1}'.format(addr.mac, addr.ip))

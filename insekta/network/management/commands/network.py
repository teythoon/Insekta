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
            try:
                amount = int(args[1])
            except ValueError:
                raise CommandError('Ehm, that is not a valid amount!')
            except IndexError:
                amount = 100

            for addr in Address.objects.fill_pool(amount):
                print('{0}={1}'.format(addr.mac, addr.ip))
            print('\nInserted {0} addresses.'.format(amount))
        elif args[0] == 'dump':
            for addr in Address.objects.all():
                print('{0}\t{1}'.format(addr.mac, addr.ip))

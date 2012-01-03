from __future__ import print_function

import os
import json
import subprocess
import re
from optparse import make_option

import libvirt
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from insekta.scenario.models import Scenario, Secret
from insekta.common.virt import connections

CHUNK_SIZE = 8192
_REQUIRED_KEYS = ['name', 'title', 'memory', 'secrets', 'image']

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--skipupload',
                    action='store_true',
                    dest='skip_upload',
                    default=False,
                    help='Do not upload the scenario image'),
    )

    args = '<scenario_path>'
    help = 'Loads a scenario into the database and storage pool'
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('The only arg is the scenario directory')
        
        scenario_dir = args[0]
       
        # Parsing metadata
        try:
            with open(os.path.join(scenario_dir, 'metadata.json')) as f_meta:
                metadata = json.load(f_meta)
                if not isinstance(metadata, dict):
                    raise ValueError('Metadata must be a dictionary')
        except IOError, e:
            raise CommandError('Could not load metadata: {0}'.format(e))
        except ValueError, e:
            raise CommandError('Could not parse metadata: {0}'.format(e))
       
        # Validating metadata
        for required_key in _REQUIRED_KEYS:
            if required_key not in metadata:
                raise CommandError('Metadata requires the key{0}'.format(
                        required_key))
       
        # Validating secrets
        secrets = metadata['secrets']
        if (not isinstance(secrets, list) or not all(isinstance(x, basestring)
                for x in secrets)):
            raise CommandError('Secrets must be a list of strings')

        # Reading description
        description_file = os.path.join(scenario_dir, 'description.creole')
        try:
            with open(description_file) as f_description:
                description = f_description.read()
        except IOError, e:
            raise CommandError('Could not read description: {0}'.format(e))

        # Checking image
        scenario_img = os.path.join(scenario_dir, metadata['image'])
        if not os.path.exists(scenario_img):
            raise CommandError('Image file is missing')
        if not os.path.isfile(scenario_img):
            raise CommandError('Image file is not a file')
        
        # Getting virtual size by calling qemu-img
        qemu_img = getattr(settings, 'QEMU_IMG_BINARY', '/usr/bin/qemu-img')
        p = subprocess.Popen([qemu_img, 'info', scenario_img],
                             stdout=subprocess.PIPE)
        stdout, _stderr = p.communicate()
        match = re.search('virtual size:.*?\((\d+) bytes\)', stdout)
        if not match:
            raise CommandError('Invalid image file format')
       
        scenario_size = int(match.group(1))

        self._create_scenario(metadata, description, scenario_img,
                              scenario_size, options)

    def _create_scenario(self, metadata, description, scenario_img,
                         scenario_size, options):
        try:
            scenario = Scenario.objects.get(name=metadata['name'])
            was_enabled = scenario.enabled
            scenario.title = metadata['title']
            scenario.memory = metadata['memory']
            scenario.description = description
            scenario.enabled = False
            created = False
            print('Updating scenario ...')
        except Scenario.DoesNotExist:
            scenario = Scenario(name=metadata['name'], title=
                    metadata['title'], memory=metadata['memory'],
                    description=description)
            created = True
            print('Creating scenario ...')
        
        scenario.save()

        print('Importing secrets for scenario ...')
        for scenario_secret in Secret.objects.filter(scenario=scenario):
            if scenario_secret.secret not in metadata['secrets']:
                scenario_secret.delete()

        for secret in metadata['secrets']:
            Secret.objects.get_or_create(scenario=scenario, secret=secret)

        print('Storing image on all nodes:')
        for node in scenario.get_nodes():
            volume = self._update_volume(node, scenario, scenario_size)

            if not options['skip_upload']:
                self._upload_image(node, scenario_img, scenario_size, volume)


            connections.close()

        if not created:
            scenario.enabled = was_enabled
            scenario.save()
        
        enable_str = 'is' if scenario.enabled else 'is NOT'
        print('Done! Scenario {0} enabled'.format(enable_str))

    def _update_volume(self, node, scenario, scenario_size):
        try:
            volume = scenario.get_volume(node)
            volume.delete(flags=0)
        except libvirt.libvirtError:
            pass
        
        print('Creating volume on node {0} ...'.format(node))
        pool = scenario.get_pool(node)
        xml_desc = """
        <volume>
          <name>{0}</name>
          <capacity>{1}</capacity>
          <target>
            <format type='qcow2' />
          </target>
        </volume>
        """.format(scenario.name, scenario_size)
        return pool.createXML(xml_desc, flags=0)

    def _upload_image(self, node, scenario_img, scenario_size, volume):
        print('Uploading image to this volume ...')
        stream = connections[node].newStream(flags=0)
        stream.upload(volume, offset=0, length=scenario_size, flags=0)
        with open(scenario_img) as f_scenario:
            while True:
                data = f_scenario.read(CHUNK_SIZE)
                if not data:
                    stream.finish()
                    break
                
                # Backward-compatibility for older libvirt versions
                try:
                    stream.send(data)
                except TypeError:
                    stream.send(data, len(data))

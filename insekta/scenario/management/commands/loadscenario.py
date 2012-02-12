from __future__ import print_function

import os
import json
import subprocess
import re
import shutil
from optparse import make_option

import libvirt
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from insekta.scenario.models import Scenario, Secret
from insekta.scenario.markup.parsesecrets import extract_secrets
from insekta.common.virt import connections
from insekta.common.misc import progress_bar

CHUNK_SIZE = 8192
_REQUIRED_KEYS = ['name', 'title', 'memory', 'image']

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

        # Directory containing static media files for the scenario
        media_dir = os.path.join(scenario_dir, 'media')

        self._create_scenario(metadata, description, scenario_img,
                              scenario_size, media_dir, options)

    def _create_scenario(self, metadata, description, scenario_img,
                         scenario_size, media_dir, options):
        secrets = extract_secrets(description)
        num_secrets = len(secrets)
        try:
            scenario = Scenario.objects.get(name=metadata['name'])
            was_enabled = scenario.enabled
            scenario.title = metadata['title']
            scenario.memory = metadata['memory']
            scenario.description = description
            scenario.num_secrets = num_secrets 
            scenario.enabled = False
            created = False
            print('Updating scenario ...')
        except Scenario.DoesNotExist:
            scenario = Scenario(name=metadata['name'], title=
                    metadata['title'], memory=metadata['memory'],
                    description=description, num_secrets=num_secrets)
            created = True
            print('Creating scenario ...')
        
        scenario.save()

        print('Importing secrets for scenario ...')
        for scenario_secret in Secret.objects.filter(scenario=scenario):
            if scenario_secret.secret not in secrets:
                scenario_secret.delete()

        for secret in secrets:
            Secret.objects.get_or_create(scenario=scenario, secret=secret)

        print('Copying media files ...')
        media_target = os.path.join(settings.MEDIA_ROOT, metadata['name'])
        
        # Remove old media dir if it exists, otherwise just ignore errors
        shutil.rmtree(media_target, ignore_errors=True)

        if os.path.exists(media_dir):
            shutil.copytree(media_dir, media_target)

        print('Storing image on all nodes:')
        for node in scenario.get_nodes():
            if not options['skip_upload']:
                volume = self._update_volume(node, scenario, scenario_size)
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
        progress = progress_bar(os.stat(scenario_img).st_size)
        data_sent = 0
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

                data_sent += len(data)
                progress.send(data_sent)
        print()

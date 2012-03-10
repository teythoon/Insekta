from __future__ import print_function
import time
import signal
from datetime import datetime

from django.core.management.base import NoArgsCommand
from django.conf import settings

from insekta.common.virt import connections
from insekta.scenario.models import ScenarioRun, RunTaskQueue, ScenarioError
from insekta.vm.models import VirtualMachineError

MIN_SLEEP = 1.0

class Command(NoArgsCommand):
    help = 'Manages the state changes of virtual machines'

    def handle_noargs(self, **options):
        self.run = True
        signal.signal(signal.SIGINT, lambda sig, frame: self.stop())
        signal.signal(signal.SIGTERM, lambda sig, frame: self.stop())

        last_call = time.time()
        while self.run:
            # Process all open tasks
            for task in RunTaskQueue.objects.all():
                try:
                    self._handle_task(task)
                except ScenarioError:
                    # This can happen if someone manages the vm manually.
                    # We can just ignore it, it does no harm
                    pass
                task.delete()
           
            # Delete expired scenarios
            expired_runs = ScenarioRun.objects.filter(last_activity__lt=
                    datetime.today() - settings.SCENARIO_EXPIRE_TIME)
            for scenario_run in expired_runs:
                try:
                    scenario_run.vm.destroy()
                except VirtualMachineError:
                    # We have an inconsistent state. See comment above.
                    pass

            current_time = time.time()
            time_passed = current_time - last_call
            if time_passed < MIN_SLEEP:
                time.sleep(MIN_SLEEP - time_passed)
            last_call = current_time
        connections.close()

    def _handle_task(self, task):
        scenario_run = task.scenario_run
        vm = scenario_run.vm

        db_state = vm.state
        vm.refresh_state()
        if vm.state != db_state:
            vm.save()

        # Scenario run was deleted in a previous task, we need to ignore
        # all further task actions except create
        if vm.state == 'disabled' and task.action != 'create':
            return
        
        if task.action == 'create':
            if vm.state == 'disabled':
                vm.create_domain()
                vm.start()
        elif task.action == 'start':
            if vm.state == 'stopped':
                vm.start()
        elif task.action == 'stop':
            if vm.state == 'started':
                vm.stop()
        elif task.action == 'suspend':
            if vm.state == 'started':
                vm.suspend()
        elif task.action == 'resume':
            if vm.state == 'suspended':
                vm.resume()
        elif task.action == 'destroy':
            vm.destroy()

    def stop(self):
        print('Stopping, please wait a few moments.')
        self.run = False

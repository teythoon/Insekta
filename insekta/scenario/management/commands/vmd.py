from __future__ import print_function
import time

from django.core.management.base import NoArgsCommand

from insekta.scenario.models import RunTaskQueue, ScenarioError

MIN_SLEEP = 1.0

class Command(NoArgsCommand):
    help = 'Manages the state changes of virtual machines'

    def handle_noargs(self, **options):
        last_call = time.time()
        while True:
            for task in RunTaskQueue.objects.all():
                try:
                    self._handle_task(task)
                except ScenarioError:
                    # This can happen if someone manages the vm manually.
                    # We can just ignore it, it does no harm
                    pass
                task.delete()
            current_time = time.time()
            time_passed = current_time - last_call
            if time_passed < MIN_SLEEP:
                time.sleep(MIN_SLEEP - time_passed)
            last_call = current_time

    def _handle_task(self, task):
        scenario_run = task.scenario_run

        db_state = scenario_run.state
        scenario_run.refresh_state()
        if scenario_run.state != db_state:
            scenario_run.save()

        # Scenario run was deleted in a previous task, we need to ignore
        # all further task actions except create
        if scenario_run.state == 'disabled' and task.action != 'create':
            return
        
        if task.action == 'create':
            if scenario_run.state == 'disabled':
                scenario_run.create_domain()
        elif task.action == 'start':
            if scenario_run.state == 'stopped':
                scenario_run.start()
        elif task.action == 'stop':
            if scenario_run.state == 'started':
                scenario_run.stop()
        elif task.action == 'suspend':
            if scenario_run.state == 'started':
                scenario_run.suspend()
        elif task.action == 'resume':
            if scenario_run.state == 'suspended':
                scenario_run.resume()
        elif task.action == 'destroy':
            scenario_run.destroy_domain()
            scenario_run.delete()

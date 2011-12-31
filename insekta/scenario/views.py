from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.middleware.csrf import get_token

from insekta.scenario.models import (Scenario, ScenarioRun, InvalidSecret,
                                     calculate_secret_token)
from insekta.scenario.creole import render_scenario

@login_required
def scenario_overview(request):
    """Show an overview of the scenarios in groups."""
    return TemplateResponse(request, 'scenario/overview.html', {

    })

@login_required
def all_scenarios(request):
    """Show all scenarios as list."""
    return TemplateResponse(request, 'scenario/all.html', {

    })

@login_required
def show_scenario(request, scenario_name):
    """Shows the description of a scenario."""
    scenario = get_object_or_404(Scenario, name=scenario_name, enabled=True)

    try:
        scenario_run = ScenarioRun.objects.get(user=request.user,
                                               scenario=scenario)
        vm_state = scenario_run.state
    except ScenarioRun.DoesNotExist:
        vm_state = 'disabled'

    environ = {
        'vm_target': reverse('scenario.manage_vm', args=(scenario_name, )),
        'vm_state': vm_state,
        'user': request.user,
        'enter_secret_target': reverse('scenario.submit_secret',
                                       args=(scenario_name, )),
        'submitted_secrets': scenario.get_submitted_secrets(request.user),
        'all_secrets': scenario.get_secrets(),
        'secret_token_function': calculate_secret_token,
        'csrf_token': get_token(request)

    }
    return TemplateResponse(request, 'scenario/show.html', {
        'scenario': scenario,
        'description': render_scenario(scenario.description, environ=environ),
    })

@login_required
def manage_vm(request, scenario_name):
    scenario = get_object_or_404(Scenario, name=scenario_name, enabled=True)

    # FIXME: Transfer this calls to a daemon with a task queue
    # FIXME: Do better checking if there is already a scenario run
    # FIXME: THIS IS REALLY ONLY TEMPORARILY!
    if 'activate' in request.POST:
        scenario_run = scenario.start(request.user)
        scenario_run.create_domain()
    else:
        scenario_run = get_object_or_404(ScenarioRun, user=request.user,
                                         scenario=scenario)
        if 'start' in request.POST:
            scenario_run.start()
        if 'resume' in request.POST:
            scenario_run.resume()
        elif 'suspend' in request.POST:
            scenario_run.suspend()
        elif 'stop' in request.POST:
            scenario_run.stop()
        elif 'deactivate' in request.POST:
            scenario_run.destroy_domain()
            scenario_run.delete()


    return redirect(reverse('scenario.show', args=(scenario_name, )))

@login_required
def submit_secret(request, scenario_name):
    scenario = get_object_or_404(Scenario, name=scenario_name, enabled=True)
    try:
        scenario.submit_secret(request.user, request.POST.get('secret'),
                               request.POST.getlist('secret_token'))
    except InvalidSecret, e:
        messages.error(request, str(e))
    else:
        messages.success(request, _('Congratulation! Your secret was valid.'))

    return redirect(reverse('scenario.show', args=(scenario_name, )))

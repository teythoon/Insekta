from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from insekta.scenario.models import Scenario
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
    scenario = get_object_or_404(Scenario, name=scenario_name)

    target_url = reverse('scenario.show', args=(scenario_name, ))
    environ = {
        'vm_target': target_url,
        'vm_state': 'disabled', # FIXME: Read current status
        'user': request.user,
        'enter_secret_target': target_url,
        'submitted_secrets': scenario.get_submitted_secrets(request.user)

    }
    return TemplateResponse(request, 'scenario/show.html', {
        'description': render_scenario(scenario.description, environ=environ),
    })

from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required

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
def show_scenario(request):
    """Shows the description of a scenario."""
    return TemplateResponse(request, 'scenario/show.html', {

    })

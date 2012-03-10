from operator import attrgetter

from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseNotModified)
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.middleware.csrf import get_token
from django import forms
from django.views.decorators.http import require_POST

from insekta.common.dblock import dblock
from insekta.scenario.models import (Scenario, ScenarioRun, RunTaskQueue,
                                     ScenarioGroup, ScenarioBelonging,
                                     UserProgress, InvalidSecret,
                                     calculate_secret_token, AVAILABLE_TASKS)
from insekta.scenario.markup.creole import render_scenario
from insekta.scenario.markup.parsesecrets import extract_secrets

LOCK_RUN_TASK_QUEUE = 298437

@login_required
def scenario_home(request):
    """Show an users running/suspended vms and other informations."""
    return TemplateResponse(request, 'scenario/home.html', {
        'scenario_run_list': ScenarioRun.objects.select_related().filter(
                user=request.user),
        'has_valid_cert': request.user.certificate.is_valid()
    })

@login_required
def scenario_groups(request):
    """Show an overview of the scenarios in groups."""

    all_scenarios = []

    # Build a dctionary for scenario groups with pk as key.
    # Attach attribute scenario_list to scenario group
    groups = {}
    for scenario_group in ScenarioGroup.objects.all():
        scenario_group.scenario_list = []
        groups[scenario_group.pk] = scenario_group

    # Attach attribute "rank" to scenarios and put them into
    # scenario group's scenario_list
    for belonging in  ScenarioBelonging.objects.select_related('scenario'):
        scenario = belonging.scenario
        if not scenario.enabled:
            continue
        scenario_list = groups[belonging.scenario_group.pk].scenario_list
        scenario.rank = belonging.rank
        scenario_list.append(scenario)
        all_scenarios.append(scenario)

    # Sort all scenario_lists by rank
    for group in groups.itervalues():
        group.scenario_list.sort(key=attrgetter('rank'))
    
    _attach_user_progress(all_scenarios, request.user)

    return TemplateResponse(request, 'scenario/groups.html', {
        'scenario_group_list': groups.values() 
    })

@login_required
def all_scenarios(request):
    """Show all scenarios as list."""
    scenarios = list(Scenario.objects.filter(enabled=True).order_by('title'))
    return TemplateResponse(request, 'scenario/all.html', {
        'scenario_list': _attach_user_progress(scenarios, request.user) 
    })

def _attach_user_progress(scenarios, user):
    """Attach attribute 'num_submitted_secrets' to all scenarios."""
    user_progress = {}
    for progress in UserProgress.objects.select_related('scenario').filter(
                user=user):
        user_progress[progress.scenario.pk] = progress.num_secrets

    for scenario in scenarios:
        scenario.num_submitted_secrets = user_progress.get(scenario.pk, 0)

    return scenarios

@login_required
def show_scenario(request, scenario_name):
    """Shows the description of a scenario."""
    scenario = get_object_or_404(Scenario, name=scenario_name, enabled=True)

    try:
        scenario_run = ScenarioRun.objects.get(user=request.user,
                                               scenario=scenario)
        vm = scenario_run.vm
        vm_state = vm.state
        ip = vm.address.ip
        expiry = scenario_run.expires_at
    except ScenarioRun.DoesNotExist:
        vm_state = 'disabled'
        ip = None
        expiry = None

    environ = {
        'ip': ip,
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
        'vm_state': vm_state,
        'ip': ip,
        'expiry': expiry,
        'num_submitted_secrets': _get_num_submitted_secrets(scenario,
                request.user)
    })

@login_required
def manage_vm(request, scenario_name):
    scenario = get_object_or_404(Scenario, name=scenario_name, enabled=True)
    
    try:
        scenario_run = ScenarioRun.objects.get(user=request.user,
                                               scenario=scenario)
        vm = scenario_run.vm
    except ScenarioRun.DoesNotExist:
        if request.method == 'POST':
            scenario_run = scenario.start(request.user)
        else:
            scenario_run = None
   
    # GET will check whether the action was executed
    if request.method == 'GET' and 'task_id' in request.GET:
        task_id = request.GET['task_id']
        if not RunTaskQueue.objects.filter(pk=task_id).count():
            return TemplateResponse(request, 'scenario/sidebar.html', {
                'scenario': scenario,
                'vm_state': vm.state if scenario_run else 'disabled',
                'ip': vm.address.ip if scenario_run else None,
                'num_submitted_secrets': _get_num_submitted_secrets(scenario,
                        request.user)
            })
        else:
            return HttpResponseNotModified()
    # while POST asks the daemon to execute the action
    elif request.method == 'POST':
        action = request.POST.get('action')

        if not action or action not in AVAILABLE_TASKS:
            raise HttpResponseBadRequest('Action not available')

        scenario_run.heartbeat()

        # FIXME: Implement some way to prevent spamming (aka. DoS)
        # Checking is done in the daemon, here we just assume that
        # everything will work fine
        
       
        with dblock(LOCK_RUN_TASK_QUEUE):
            try:
                task = RunTaskQueue.objects.get(scenario_run=scenario_run)
            except RunTaskQueue.DoesNotExist:
                task = RunTaskQueue.objects.create(scenario_run=scenario_run,
                                                   action=action)
        if request.is_ajax():
            return HttpResponse('{{"task_id": {0}}}'.format(task.pk),
                                mimetype='application/x-json')
        else:
            messages.success(request, _('Task was received and will be executed.'))
    
    return redirect(reverse('scenario.show', args=(scenario_name, )))

@require_POST
@login_required
def heartbeat(request, scenario_name):
    scenario = get_object_or_404(Scenario, name=scenario_name, enabled=True)
    try:
        scenario.get_run(request.user).heartbeat()
    except ScenarioRun.DoesNotExist:
        pass
    
    return redirect(reverse('scenario.show', args=(scenario_name, )))

def _get_num_submitted_secrets(scenario, user):
    try:
        return (UserProgress.objects.get(user=user, scenario=scenario)
                .num_secrets)
    except UserProgress.DoesNotExist:
        return 0

@login_required
def submit_secret(request, scenario_name):
    scenario = get_object_or_404(Scenario, name=scenario_name, enabled=True)
    try:
        scenario.get_run(request.user).heartbeat()
    except ScenarioRun.DoesNotExist:
        pass

    try:
        scenario.submit_secret(request.user, request.POST.get('secret'),
                               request.POST.getlist('secret_token'))
    except InvalidSecret, e:
        messages.error(request, unicode(e))
    else:
        messages.success(request, _('Congratulation! Your secret was valid.'))

    return redirect(reverse('scenario.show', args=(scenario_name, )))

@login_required
@permission_required('scenario.view_editor')
def editor(request):
    class EditorForm(forms.Form):
        submitted_secrets = forms.CharField(label=_('Submitted secrets:'),
                widget=forms.Textarea(attrs={'cols': 35, 'rows': 5}),
                required=False)
        content = forms.CharField(label=_('Content:'),
                widget=forms.Textarea(attrs={'cols': 80, 'rows': 30}),
                required=False)

    def parse_secrets(secrets):
        return [secret.strip() for secret in secrets.splitlines()]

    secrets = None
    if request.method == 'POST':
        editor_form = EditorForm(request.POST)
        if editor_form.is_valid():
            data = editor_form.cleaned_data
            secrets = extract_secrets(data['content'])
            environ = {
                'submitted_secrets': parse_secrets(data['submitted_secrets']),
                'all_secrets': secrets,
                'secret_token_function': calculate_secret_token,
                'user': request.user,
                'enter_secret_target': 'javascript:return false;',
                'csrf_token': ''
            }
            preview = render_scenario(data['content'], environ=environ)
        else:
            preview = None
    else:
        editor_form = EditorForm()
        preview = None
    
    return TemplateResponse(request, 'scenario/editor.html', {
        'editor_form': editor_form,
        'preview': preview,
        'secrets': secrets
    })


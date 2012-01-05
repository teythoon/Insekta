from django.contrib import admin

from insekta.scenario.models import (Scenario, Secret, ScenarioRun,
                                     SubmittedSecret, ScenarioGroup,
                                     ScenarioBelonging)

class SecretInline(admin.TabularInline):
    model = Secret

class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'hypervisor', 'memory', 'enabled')
    inlines = [SecretInline]


def scenario_name(obj):
    return obj.scenario.name
scenario_name.short_description = 'Scenario name'

def scenario_title(obj):
    return obj.scenario.title
scenario_title.short_description = 'Scenario title'

class ScenarioRunAdmin(admin.ModelAdmin):
    list_display = ('user', 'state', scenario_name, scenario_title)


def secret(obj):
    return obj.secret.secret
secret.short_description = 'Secret'

def secret_scenario_title(obj):
    return obj.secret.scenario.title
secret_scenario_title.short_description = 'Scenario title'

class SubmittedSecretAdmin(admin.ModelAdmin):
    list_display = ('user', secret, secret_scenario_title)


class ScenarioBelongingInline(admin.TabularInline):
    model = ScenarioBelonging
    ordering = ('rank', )

class ScenarioGroupAdmin(admin.ModelAdmin):
    inlines = [ScenarioBelongingInline]

admin.site.register(Scenario, ScenarioAdmin)
admin.site.register(ScenarioRun, ScenarioRunAdmin)
admin.site.register(SubmittedSecret, SubmittedSecretAdmin)
admin.site.register(ScenarioGroup, ScenarioGroupAdmin)

from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('insekta.scenario.views',
   url(r'^$', 'scenario_overview', name='scenario.overview'),
   url(r'^all$', 'all_scenarios', name='scenario.all'),
   url(r'^show/([\w-]+)$', 'show_scenario', name='show_scenario'),
)

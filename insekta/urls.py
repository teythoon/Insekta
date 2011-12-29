from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'insekta.views.home', name='home'),
    url(r'^scenario/', include('insekta.scenario.urls')),

    url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login'),

    url(r'^admin/', include(admin.site.urls)),
)

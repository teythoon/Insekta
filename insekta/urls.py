from django.conf.urls.defaults import patterns, include, url
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', lambda request: redirect(reverse('scenario.home'))),
    url(r'^scenario/', include('insekta.scenario.urls')),
    url(r'^certificate/', include('insekta.pki.urls')),
    
    url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login'),

    url(r'^admin/', include(admin.site.urls)),
)

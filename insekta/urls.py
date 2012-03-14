from django.conf.urls.defaults import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', lambda request: redirect(reverse('scenario.home'))),
    url(r'^scenario/', include('insekta.scenario.urls')),
    url(r'^certificate/', include('insekta.pki.urls')),
    url(r'^accounts/', include('insekta.registration.urls')),

    url(r'^admin/', include(admin.site.urls)),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

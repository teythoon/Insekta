from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^login', 'django.contrib.auth.views.login'),
    url(r'^logout', 'django.contrib.auth.views.logout_then_login'),
)

urlpatterns += patterns('insekta.registration.views',
    url(r'^registration$', 'registration', name='registration.registration'),
    url(r'^pending/(\w+)/(\w+)$', 'pending', name='registration.pending'),
)

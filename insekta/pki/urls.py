from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('insekta.pki.views',
   url(r'^$', 'home', name='pki.home'),
   url(r'^certificate.zip$', 'download_cert', name='pki.download_cert'),
)

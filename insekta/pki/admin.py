from datetime import datetime

from django.contrib import admin

from insekta.pki.models import Certificate

def information(obj):
    if not obj.certificate:
        return u'Certificate not generated'
    elif obj.expires < datetime.utcnow():
        return u'Certificate is expired ({0})'.format(obj.expires)
    else:
        return u'Certificate expires at {0}'.format(obj.expires)
information.short_description = 'Certificate information'

class CertificateAdmin(admin.ModelAdmin):
    list_display = ('user', information)

admin.site.register(Certificate, CertificateAdmin)


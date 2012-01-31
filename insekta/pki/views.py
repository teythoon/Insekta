from zipfile import ZipFile
from contextlib import closing
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from M2Crypto import X509
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, user_passes_test
from django import forms
from django.http import HttpResponse
from django.conf import settings

@login_required
def home(request):
    class CsrForm(forms.Form):
        csr = forms.CharField(widget=forms.Textarea(attrs={'cols': 70,
                                                           'rows': 20}))
        
        def clean_csr(self):
            data = self.cleaned_data
            try:
                # X509.load_request_string doesn't like unicode
                data['csr'] = X509.load_request_string(data['csr'].encode('utf-8'))
            except X509.X509Error:
                raise forms.ValidationError(_('Invalid CSR.'))
            return data['csr']

    cert = request.user.certificate
    if request.method == 'POST':
        csr_form = CsrForm(request.POST)
        if csr_form.is_valid() and not cert.is_valid():
            cert.generate_certificate(csr_form.cleaned_data['csr'])
            return redirect(reverse('pki.home'))
    else:
        csr_form = CsrForm()

    return TemplateResponse(request, 'pki/home.html', {
        'certificate': cert,
        'csr_form': csr_form
    })

@login_required
@user_passes_test(lambda u: u.certificate.is_valid())
def download_cert(request):
    zip_content = StringIO()
    with closing(ZipFile(zip_content, 'w')) as zip_file:
        cert_content = request.user.certificate.certificate.encode('utf-8')
        zip_file.writestr('certificate.pem', cert_content)
        zip_file.write(settings.PKI_CA_CERTFILE, 'ca.crt')
        zip_file.write(settings.PKI_OPENVPN_CONFIG, 'client.conf')
    return HttpResponse(zip_content.getvalue(),
                        mimetype='application/x-zip-compressed')

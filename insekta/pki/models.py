import time
from datetime import datetime

from M2Crypto import EVP, X509, ASN1
from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.conf import settings

class Certificate(models.Model):
    user = models.OneToOneField(User)
    certificate = models.TextField(null=True, blank=True, default=None)
    expires = models.DateTimeField(null=True, blank=True, default=None)

    def generate_certificate(self, csr):
        """Generate and sign a certificate and store it in database.

        :param csr: Certificate Signing Request. See :class:`M2Crypto.X509.Request`.
        :return: Generated + signed certificate. It is an instance of
                 :class:`M2Crypto.X509.X509`.
        """
        cert = generate_certificate(csr, self.pk, self.user.username)
        expires = cert.get_not_after().get_datetime()
        self.certificate = cert.as_pem()
        self.expires = expires
        self.save()
        return cert

    def is_valid(self):
        return self.certificate and self.expires > datetime.utcnow()

def generate_certificate(csr, serial, cn):
    """Generate a certificate and sign it with CA.

    :param csr: Certificate Signing Request. See :class:`M2Crypto.X509.Request`.
    :param serial: Serial number of the certificate as long int.
    :param cn: Common Name of the certificate.
    :return: Generated + signed certificate. See :class:`M2Crypto.X509.X509`.
    """
    ca_key = EVP.load_key(settings.PKI_CA_KEYFILE, lambda *args: None)
    ca_cert = X509.load_cert(settings.PKI_CA_CERTFILE)
    
    cert = X509.X509()
    cert.set_serial_number(serial)
    cert.set_version(2)
    csr_subject = csr.get_subject()
    subject = X509.X509_Name()
    for key in ('C', 'ST', 'L', 'O', 'OU'):
        original_value = getattr(csr_subject, key)
        if original_value:
            setattr(subject, key, original_value)
    subject.CN = cn
    cert.set_subject(subject)
    t = long(time.time()) + time.timezone
    now = ASN1.ASN1_UTCTIME()
    now.set_time(t)
    now_plus_year = ASN1.ASN1_UTCTIME()
    now_plus_year.set_time(t + 60 * 60 * 24 * 365)
    cert.set_not_before(now)
    cert.set_not_after(now_plus_year)
    cert.set_issuer(ca_cert.get_subject())
    cert.set_pubkey(csr.get_pubkey())
    cert.sign(ca_key, 'sha1')
    return cert

def _create_user_cb(sender, instance, created, **kwargs):
    """Create an certificate object for each new user. """
    if created:
        Certificate.objects.create(user=instance)
post_save.connect(_create_user_cb, sender=User)

import hashlib
import hmac

from django.conf import settings
from django import forms
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegisterForm(UserCreationForm):
    email = forms.EmailField()

def registration(request):
    if request.method == 'POST':
        register_form = RegisterForm(request.POST)
        
        if register_form.is_valid():
            data = register_form.cleaned_data
            verification_hash = _username_verification_hash(data['username'])
            user = User.objects.create_user(data['username'], data['email'],
                                            data['password1'])
            user.is_active = False
            user.save()
            return redirect(reverse('registration.pending',
                args=(data['username'], verification_hash)))
    else:
        register_form = RegisterForm()

    return TemplateResponse(request, 'registration/registration.html', {
        'register_form': register_form
    })

def pending(request, username, verification_hash):
    if verification_hash != _username_verification_hash(username):
        raise PermissionDenied('Invalid signing')

    user = get_object_or_404(User, username=username)
    return TemplateResponse(request, 'registration/pending.html', {
        'checked_user': user   
    })

def _username_verification_hash(username):
    return hmac.new(settings.SECRET_KEY, username, hashlib.sha1).hexdigest()

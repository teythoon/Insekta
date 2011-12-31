import hashlib
import hmac
from genshi.builder import tag
from creoleparser import Parser, create_dialect, creole11_base
from django.utils.translation import ugettext as _
from django.conf import settings

def vmbox(macro, environ):
    """Macro for showing a box with information and actions for a vm.
    
    Requires the following keys in the environ:

    ``vm_target``
       An url for the action attribute of the form element. Submitting the
       form will generate a POST request will contain of of the following
       keys: ``activate``, ``deactivate``, ``start``, ``suspend`` and
       ``stop`` with an undefined value.

    ``vm_state``
       One of ``disabled``, ``started``, ``stopped``, ``suspended`` and
       ``preparing``. The state ``preparing`` signalizes an ongoing state
       change.
    
    ``csrf_token``
       Django's CSRF token. Use :func:`django.middleware.csrf.get_token` to
       get it.
    """
   
    actions = {
        'start': tag.input(type='submit', name='start', value=_('Start')),
        'stop': tag.input(type='submit', name='stop', value=_('Stop')),
        'suspend': tag.input(type='submit', name='suspend', value=_('Suspend')),
        'resume': tag.input(type='submit', name='resume', value=_('Resume')),
        'deactivate': tag.input(type='submit', name='deactivate',
                                value=_('Deactivate')),
        'activate': tag.input(type='submit', name='activate',
                              value=_('Activate')),
    }

    text_state = {
        'disabled': _('Your virtual machine is not activated yet.'),
        'started': _('Your virtual machine is running at {ip}.').format(
            ip=environ.get('ip', 'unknown ip')),
        'stopped': _('Your virtual machine ({ip}) is stopped.').format(
            ip=environ.get('ip', 'unknown ip')),
        'suspended': _('Your virtual machine ({ip}) is suspended.').format(
            ip=environ.get('ip', 'unknown ip'))
    }[environ['vm_state']]
    
    enabled_actions = {
        'disabled': (actions['activate'], ),
        'started': (actions['suspend'], actions['stop']),
        'stopped': (actions['start'], actions['deactivate']),
        'suspended': (actions['resume'], actions['deactivate'])
    }[environ['vm_state']]

    form = tag.form(method='post', action=environ['vm_target'])
    for action in enabled_actions:
        form.append(action)

    form.append(tag.input(type='hidden', name='csrfmiddlewaretoken',
                          value=environ['csrf_token']))
   
    title = tag.span(_('Managing the virtual machine'), class_='vmbox_title')
    text_actions = _('Choose one of the following actions:')

    vmbox = tag.div(class_='vmbox')
    vmbox.append(title)
    vmbox.append(tag.p(text_state))
    vmbox.append(tag.p(text_actions))
    vmbox.append(form)
    return vmbox

def enter_secret(macro, environ, *secrets):
    """Macro for entering a secret. Takes a several secrets as args.

    Requires the following keys in the environ:
    
    ``user``
       An instance of :class:`django.contrib.auth.models.User`. Will be used
       to generate a security token of a secret that is only valid for this
       user.

    ``enter_secret_target``
       An url for the action attribute of the form element. Submitting the
       form will generate a POST request with the following data:

       ``secret``
          The secret which was entered by the user

       ``secret_token``
          Occurs several times, one time for each secret that is valid for
          this form. It is a security token that is build by generating
          a HMAC with ``settings.SECRET_KEY`` as key. The message is the
          user id and the valid secret divided by a colon.

    ``all_secrets``
       A list of strings containing all available secrets for this scenario.
    
    ``submitted_secrets``
       A list of strings containing all secrets submitted by the user for
       this scenario.

    ``secret_token_function``
       A function that calculates the secret's security token. Takes an user
       and a secret.

    ``csrf_token``
       Django's CSRF token. Use :func:`django.middleware.csrf.get_token` to
       get it.
    """
    target = environ['enter_secret_target']
    user = environ['user']
    
    form = tag.form(macro.parsed_body(), method='post', action=target)

    # If there are no secrets in the arguments, we will accept all secrets
    if not secrets:
        secrets = environ['all_secrets']

    # If all secrets are already submitted, hide this box
    if all(secret in environ['submitted_secrets'] for secret in secrets):
        return ''
   
    for secret in secrets:
        secret_token = environ['secret_token_function'](user, secret)
        form.append(tag.input(name='secret_token', value=secret_token,
                              type='hidden'))
    
    form.append(tag.input(type='hidden', name='csrfmiddlewaretoken',
                          value=environ['csrf_token']))

    p = tag.p(_('Enter secret:'))
    p.append(tag.input(name='secret', type='text'))
    p.append(tag.input(type='submit', name='enter_secret', value=_('Submit')))
    form.append(p)

    return tag.div(form, class_='enter_secret')

def require_secret(macro, environ, *secrets):
    """Macro for hiding text that can be shown by submitting a secret.

    You can provide several secrets as arguments. If ANY of the secret
    was submitted by the user, the content is shown.

    Requires the following keys in the environ:

    ``submitted_secrets``
       A set of secrets for this scenario which were submitted by the user.
    """
    show_content = any(x in environ['submitted_secrets'] for x in secrets)

    if show_content:
        return macro.parsed_body()
    else:
        text = _('Here is some hidden content.'
                  'You need to enter a specific secret to show it.')
        return tag.div(tag.p(text), class_='require_secret')

def spoiler(macro, environ):
    """Macro for spoiler. Showing and hiding it is done via javascript."""
    return tag.div(macro.parsed_body(), class_='spoiler')

def ip(macro, environ):
    """Macro for the virtual machine's ip."""
    ip = environ.get('ip')
    if not ip:
        ip = '127.0.0.1'
    return tag.span(ip, class_='ip')

_non_bodied_macros = {'vmBox': vmbox, 'ip': ip}
_bodied_macros = {
    'enterSecret': enter_secret,
    'requireSecret': require_secret,
    'spoiler': spoiler
}
_dialect = create_dialect(creole11_base, non_bodied_macros=_non_bodied_macros,
        bodied_macros=_bodied_macros)

render_scenario = Parser(dialect=_dialect, method='xhtml')

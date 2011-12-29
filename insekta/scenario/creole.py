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
       One of ``disabled``, ``started`` and ``stopped``. Suspended machines
       are in the state ``stopped``.
    """
   
    actions = {
        'start': tag.input(type='submit', name='start', value=_('Start')),
        'suspend': tag.input(type='submit', name='suspend', value=_('Suspend')),
        'stop': tag.input(type='submit', name='stop', value=_('Stop')),
        'deactivate': tag.input(type='submit', name='deactivate',
                                value=_('Deactivate')),
        'activate': tag.input(type='submit', name='activate',
                              value=_('Activate')),
    }
    
    enabled_actions = {
        'disabled': (actions['activate'], ),
        'started': (actions['suspend'], actions['stop']),
        'stopped': (actions['start'], actions['deactivate'])
    }[environ['vm_state']]

    form = tag.form(method='post', action=environ['vm_target'])
    for action in enabled_actions:
        form.append(action)
   
    title = tag.span(_('Managing the virtual machine'), class_='vm_title')
    text = _('Choose one of the following actions:')

    vmbox = tag.div(class_='vmbox')
    vmbox.append(title)
    vmbox.append(text)
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
    """
    target = environ['enter_secret_target']
    user = environ['user']
    
    form = tag.form(macro.parsed_body(), method='post', action=target)
   
    for secret in secrets:
        msg = '{0}:{1}'.format(user.pk, secret)
        hmac_gen = hmac.new(settings.SECRET_KEY, msg, hashlib.sha1())
        secret_token = hmac_gen.hexdigest()
        form.append(tag.input(name='secret_token', value=secret_token,
                              type='hidden'))

    p = tag.p(_('Enter secret:'))
    p.append(tag.input(name='secret', type='text'))
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

_non_bodied_macros = {'vmBox': vmbox}
_bodied_macros = {
    'enterSecret': enter_secret,
    'requireSecret': require_secret,
    'spoiler': spoiler
}
_dialect = create_dialect(creole11_base, non_bodied_macros=_non_bodied_macros,
        bodied_macros=_bodied_macros)

render_scenario = Parser(dialect=_dialect, method='xhtml')

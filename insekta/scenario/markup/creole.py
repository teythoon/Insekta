import re
from genshi.builder import tag
from genshi import Markup
from creoleparser import Parser, create_dialect, creole11_base
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.conf import settings
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
from insekta.scenario.markup.highlight import highlight_parts

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

    p = tag.p(tag.strong(_('Enter secret:')), ' ')
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
        dragons = tag.strong(_('Here be dragons.'))
        text = _('This content is hidden, '
                  'you need to submit a specific secret in order to show it.')
        return tag.div(tag.p(dragons, ' ', text), class_='require_secret')

def spoiler(macro, environ):
    """Macro for spoiler. Showing and hiding it is done via javascript."""
    return tag.div(macro.parsed_body(), class_='spoiler')

def ip(macro, environ):
    """Macro for the virtual machine's ip."""
    ip = environ.get('ip')
    if not ip:
        ip = '127.0.0.1'
    return tag.span(ip, class_='ip')

def code(macro, environ, lang='text', linenos=False):
    """Macro for syntax highlighting using pygments."""
    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        return tag.div(_('No such language: {lang}').format(lang=lang),
                       class_='error')
    formatter = HtmlFormatter(linenos=linenos == 'yes')
    return Markup(highlight(macro.body, lexer, formatter))

_highlight_colors = {
    '!': '#d00',
    '^': '#00d',
    '~': '#d50',
    '-': '#0dd'
}
color_re = re.compile('^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$')
def color(macro, environ, color):
    """Macro for coloring text. Supports also highlight chars as color."""
    color = _highlight_colors.get(color, color)
    # Prevent against CSS injections.
    if not (color.isalpha() or color_re.match(color)):
        color = 'black'
    container = tag.p if macro.isblock else tag.span
    return container(macro.parsed_body(), style='color:{0};'.format(color))

def highlight_(macro, environ):
    """Macro for highlighting some parts using special markup::
       
       Lorem ipsum dolor si amet
             ^^^^^       ^^
       consectetur adipiscing elit
       Mauris ac magna a nisl ornare
              ^^^^^^^^   ^^^^
    """
    def marking(some_str, char):
        return '<<color {0}>>**{1}**<</color>>'.format(char, some_str)

    return highlight_parts(macro.body, marking)


comment_re = re.compile('\{#(.+?)#\}')
def comment(match, environ):
    return Markup()

def wiki_link_cb(page_name):
    if page_name.startswith('media:'):
        return settings.MEDIA_URL + page_name.replace('media:', '', count=1)
    else:
        return reverse('scenario.show', args=(page_name, ))

def wiki_image_cb(page_name):
    return settings.MEDIA_URL + page_name

_non_bodied_macros = {'ip': ip}
_bodied_macros = {
    'enterSecret': enter_secret,
    'requireSecret': require_secret,
    'spoiler': spoiler,
    'code': code,
    'color': color,
    'highlight': highlight_
}
_dialect = create_dialect(creole11_base, non_bodied_macros=_non_bodied_macros,
        bodied_macros=_bodied_macros, custom_markup=[(comment_re, comment)],
        wiki_links_path_func=[wiki_link_cb, wiki_image_cb])

render_scenario = Parser(dialect=_dialect, method='xhtml')

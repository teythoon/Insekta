from creoleparser import Parser, create_dialect, creole11_base

def enter_secret(macro, environ, *secrets):
    environ['secrets'].update(secrets)

def macro_func(name, argument, body, type, environ):
    return body

_dialect = create_dialect(creole11_base, macro_func=macro_func,
        bodied_macros={'enterSecret': enter_secret},)
_render = Parser(dialect=_dialect, method='xhtml')

def extract_secrets(text):
    environ = {'secrets': set()}
    # Parse to populate environ['secrets'], discard xhtml
    _render(text, environ=environ)
    return environ['secrets']


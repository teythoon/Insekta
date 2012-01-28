from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def scenario_progress(num_submitted, num_available):
    url = settings.STATIC_URL
    gray_dot = '<img src="{0}/gray-dot.png" alt="O" />'.format(url)
    green_dot = '<img src="{0}/green-dot.png" alt="X" />'.format(url)

    num_missing = num_available - num_submitted
    return green_dot * num_submitted + gray_dot * num_missing

scenario_progress.is_safe = True

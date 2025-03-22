from django import template
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

register = template.Library()

@register.simple_tag
def is_url(string):
    validate = URLValidator()
    try:
        validate(string)
        return True
    except ValidationError:
        return False
    
@register.simple_tag
def replace_am_pm(string):
    return string.replace(' a.m.', 'a').replace(' p.m.', 'p')

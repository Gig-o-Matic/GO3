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

@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(key)
    except Exception:
        return None

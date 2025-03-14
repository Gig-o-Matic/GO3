from django import template
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from gig.models import Plan

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
def is_plan(plan):
    return isinstance(plan, Plan)
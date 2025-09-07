from zoneinfo import ZoneInfo
from django import template
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone


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

@register.filter
def utc_offset(string):
    """ takes the name of a timezone and returns the UTC offset """
    o=timezone.localtime(timezone=ZoneInfo(string)).utcoffset()
    hours = (o.days*24) + (o.seconds/3600)
    return hours

from django import template

register = template.Library()

@register.filter
def lookup_plans(value, section):
    thelist = [v.grouper for v in value]
    if (section in thelist):
        idx=thelist.index(section)
        return value[idx].list
    else:
        return []


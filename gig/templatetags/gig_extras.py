from django import template

register = template.Library()


@register.filter
def lookup_plans(value, section):
    thelist = [v.grouper for v in value]
    if section in thelist:
        idx = thelist.index(section)
        return value[idx].list
    else:
        return []


@register.filter
def lookup(value, index):
    if index == 0:
        return ""
    else:
        return value[int(index) - 1].strip()

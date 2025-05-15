from django import template
register = template.Library()

@register.filter
def dictkey(d, key):
    return d.get(int(key)) if d else None

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def dict_get(d, key):
    return d.get(str(key)) if isinstance(d, dict) else None

@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key))  # str() because template keys are strings

from django import template
register = template.Library()

@register.filter
def dictkey(d, key):
    return d.get(int(key)) if d else None

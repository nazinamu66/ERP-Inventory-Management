# your_app/templatetags/formatting.py
from django import template

register = template.Library()

@register.filter(name='money')
def money(value):
    try:
        value = float(value)
        return f"{value:,.2f}"
    except (ValueError, TypeError):
        return value

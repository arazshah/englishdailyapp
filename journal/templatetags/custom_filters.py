from django import template

register = template.Library()

@register.filter
def replace(value, arg):
    """
    Replace all instances of the first argument with the second argument.
    
    Usage: {{ value|replace:"_: " }}
    """
    if len(arg.split(':')) != 2:
        return value
    
    old, new = arg.split(':')
    return value.replace(old, new) 
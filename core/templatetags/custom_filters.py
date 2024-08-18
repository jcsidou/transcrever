# Em um arquivo como myapp/templatetags/custom_filters.py
from django import template
import datetime

register = template.Library()

@register.filter
def time_format(value):
    try:
        seconds = float(value)
        return str(datetime.timedelta(seconds=seconds)).split('.')[0].zfill(8)
    except ValueError:
        return value
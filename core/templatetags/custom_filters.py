# Em um arquivo como myapp/templatetags/custom_filters.py
from django import template
import os 
import datetime

register = template.Library()

@register.filter
def time_format(value):
    try:
        seconds = float(value)
        return str(datetime.timedelta(seconds=seconds)).split('.')[0].zfill(8)
    except ValueError:
        return value
    
@register.filter
def basename(value):
    return os.path.basename(value)

@register.filter
def sem_barra_video(value):
    value = value.replace('videos/','')
    return os.path.basename(value)
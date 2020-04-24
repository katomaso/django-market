# coding: utf-8
import logging

from django.template import Library
from django.template.defaultfilters import mark_safe

register = Library()
logger = logging.getLogger(__name__)


@register.simple_tag(takes_context=False)
def if_female(name, suffix):
    """Print out `siffix` if `name` is female in czech language."""
    if name.endswith("ová") or name.endswith("ova"):
        return mark_safe(suffix)
    return mark_safe("")

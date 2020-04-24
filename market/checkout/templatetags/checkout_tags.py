# -*- coding: utf-8 -*-
# from copy import copy
from django import template

# from market.core import models as core_models

from .. import utils

register = template.Library()


@register.inclusion_tag('checkout/public/cart-item.html', takes_context=True)
def cart(context):
    """Inclusion tag for displaying cart summary."""
    request = context['request']
    cart = utils.get_or_create_cart(request)
    cart.update(request)
    return {
        'cart': cart
    }


@register.inclusion_tag("checkout/include/add-to-cart-form.html")
def add_to_cart_form(offer, **kwargs):
    kwargs.update({
        'offer': offer,
        'number_type': kwargs.get("number_type", "number"),
    })
    return kwargs


# @register.inclusion_tag('vendor/templatetags/_order.html', takes_context=True)
# def order(context, order):
#     """Inclusion tag for displaying order."""
#     if "order" in context:
#         # do not overwrite already presented order
#         duplicate = copy(context)
#         duplicate.update({"order": order})
#         return duplicate
#     context.update({"order": order})
#     return context


# @register.inclusion_tag('vendor/templatetags/_products.html', takes_context=True)
# def products(context, *args):
#     """Inclusion tag for displaying all products. Expects one argument - an iterable."""
#     if not args:
#         context.update({'products': core_models.Product.objects.filter(active=True), })
#     else:
#         if len(args) == 1:
#             context.update({'products': args[0], })
#         else:
#             context.update({'products': args, })
#     return context

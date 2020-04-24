# coding: utf-8
from collections import defaultdict

from django.utils import six
from django.utils.translation import gettext as _
from django.shortcuts import reverse


class MappedMixin:
    """Add map_markers into context from (paginated) context['object_list']."""

    marker = None

    def get_context_data(self, **kwargs):
        """Add map markers."""
        context = super().get_context_data(**kwargs)
        assert self.marker, "Specify {}.marker!".format(self.__class__.__name__)

        if context.get('is_paginated', False):
            add_map_markers(context, [context['page_obj.object_list'], ], self.marker)

        elif "object_list" in context:
            add_map_markers(context, [context['object_list'], ], self.marker)

        elif "object" in context:
            add_map_markers(context, [context['object'], ], )

        else:
            raise RuntimeError("Nothing to mark on map!")

        return context


def add_map_markers(context, iterable, formater):
    """Entry-point for generic adding of markers into a map."""
    markers = []
    for instance in iterable:
        mark = formater(instance)
        if mark:
            if isinstance(mark, (list, tuple)):
                markers.extend(mark)
            else:
                markers.append(mark)
    if markers:
        context.update(map_markers=markers)


def vendor_marker(vendor):
    """Add vendor markers for map into context."""
    if not (vendor.position and vendor.position.lat and vendor.position.lng):
        return None
    return {
        'x': str(vendor.position.lng),
        'y': str(vendor.position.lat),
        'title': vendor.name,
        'link': reverse('vendor', kwargs={'slug': vendor.slug, 'format': 'html'}),
        'body': vendor.short_description,
        'slug': vendor.slug,
    }


def _by_vendor_marker(vendor, offers):
    if not (vendor.position and vendor.position.lat and vendor.position.lng):
        return None
    num_offers = len(offers)
    if num_offers > 1:
        return {
            "x": str(vendor.position.lng),
            "y": str(vendor.position.lat),
            "title": vendor.name,
            "link": reverse('vendor', kwargs={'slug': vendor.slug, 'format': 'html'}),
            "body": " ".join(_("Offers"), str(num_offers), _("displayed products")),
        }
    offer = offers[0]
    return {
        "x": str(vendor.position.lng),
        "y": str(vendor.position.lat),
        "title": vendor.name,
        'slug': offer.slug,
        "link": reverse('cart', kwargs={'format': 'json'}),
        "body": str(offer.price),
    }


def product_marker(product):
    """Create marks clustered by vendor position."""
    result = []
    by_vendor = defaultdict(list)
    for offer in product.offers:
        if offer.vendor.position and offer.vendor.position.lng and offer.vendor.position.lat:
            by_vendor[offer.vendor].append(offer)

    for vendor, offers in six.iteritems(by_vendor):
        result.append(_by_vendor_marker(vendor, offers))
    return result


def products_marker(products):
    """Create marks clustered by vendor position."""
    result = []
    by_vendor = defaultdict(list)
    for product in products:
        for offer in product.offers:
            if offer.vendor.position.lng and offer.vendor.position.lat:
                by_vendor[offer.vendor].append(offer)

    for vendor, offers in six.iteritems(by_vendor):
        result.append(_by_vendor_marker(vendor, offers))
    return result

from random import choice, randint

from django.db import transaction

from market.core import models as core_models
from market.core import test_data as core_test_data
from . import models


def add_item(order, offer, quantity=1):
    item, created = models.OrderItem.objects.get_or_create(
        order=order, item=offer,
        item_reference=offer.slug, item_name=offer.name, quantity=quantity,
        subtotal=offer.unit_price, total=offer.price)
    order.subtotal += item.subtotal
    order.total += item.total
    order.save()
    return item


@transaction.atomic
def load():
    core = core_test_data.load()  # {'vendors': list, 'products': list, 'core['users']': list}
    vendors = core['vendors']
    offers = core_models.Offer.objects.filter(active=True)

    order, created = models.Order.objects.get_or_create(
        vendor=vendors[0], status=models.Order.COMPLETED)

    if created:
        add_item(order, choice(offers), randint(1, 5))
        add_item(order, choice(offers), randint(1, 5))
        add_item(order, choice(offers), randint(1, 5))

        top_order = models.Order.objects.create(
            user=core['users'][2], vendor=None, status=models.Order.COMPLETED)
        top_order.shipping_address = core['users'][2].shipping_address
        top_order.billing_address = core['users'][2].billing_address
        top_order.save()

        order.order = top_order
        order.save()
        top_order.update_costs()

    order, created = models.Order.objects.get_or_create(
        vendor=vendors[0], status=models.Order.SHIPPED)

    if created:
        add_item(order, choice(offers), randint(1, 5))
        add_item(order, choice(offers), randint(1, 5))
        add_item(order, choice(offers), randint(1, 5))

        top_order = models.Order.objects.create(
            user=core['users'][2], vendor=None, status=models.Order.SHIPPED)
        top_order.shipping_address = core['users'][2].shipping_address
        top_order.billing_address = core['users'][2].billing_address
        top_order.save()

        order.order = top_order
        order.save()
        top_order.update_costs()

    order, created = models.Order.objects.get_or_create(
        vendor=vendors[0], status=models.Order.CONFIRMED)

    if created:
        add_item(order, choice(offers), randint(1, 5))
        add_item(order, choice(offers), randint(1, 5))
        add_item(order, choice(offers), randint(1, 5))

        top_order = models.Order.objects.create(
            user=core['users'][1], vendor=None, status=models.Order.CONFIRMED)
        top_order.shipping_address = core['users'][1].shipping_address
        top_order.billing_address = core['users'][1].billing_address
        top_order.save()

        order.order = top_order
        order.save()
        top_order.update_costs()

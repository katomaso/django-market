# coding: utf-8
import random
from decimal import Decimal

from market.core.models import Category, Product, Offer
from .test_data import load as base_load

products = 150


def load():
    data = base_load()
    vendors = data['vendors']

    max_offers = len(data['vendors'])
    categories = Category.objects.all()

    for i in range(products):
        product = create_product(
            name="Produkt {0}".format(i),
            vendor=random.choice(vendors),
            category=random.choice(categories),
        )
        offers = random.randint(-5, max_offers - 1)
        vendors_local = vendors[:]
        vendors_local.remove(product.vendor)
        for j in range(offers):
            vendor = random.choice(vendors_local)
            create_offer(product=product, vendor=vendor)
            vendors_local.remove(vendor)

        data['products'].append(product)
    return data


def create_product(**kwargs):
    base_product = {
        'name': 'unique',
        'active': True,
        'vendor': None,
        'manufacturer': None,
        'category': None,
        'photo': None,
        'description': '',
        'expedition_days': random.choice((0, 0, 0, 0, 1, 2, 3, 1, 0))
    }
    base_product.update(kwargs)
    product = Product.objects.create(**base_product)
    create_offer(product=product, vendor=base_product['vendor'])
    return product


def create_offer(**kwargs):
    base_offer = {
        'vendor': None,
        'product': None,
        'quantity': random.choice((-1, -1, -1, -1, -1, -1, -1, 1, 5)),
        'shipping_price': Decimal(random.choice((20, 50, 70, 80, 90, 100, 120, 150))),
        'unit_price': Decimal(random.randint(100, 100000)),
        'active': True,
    }
    base_offer.update(kwargs)
    return Offer.objects.create(**base_offer)

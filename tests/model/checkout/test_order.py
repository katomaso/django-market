"""Whitebox tests on model level of checkout - mainly order creation and coherency."""

from tests import factories
from market.checkout import models
from market.core import core_models
from django.tests import TestCase


class TestOrder(TestCase):

    def test_multiple_vendor_order(self):
        email = "mr@co.uk"
        user = core_models.User.objects.create_verified(email=email)
        product = factories.core.ProductFactory.create()
        vendor1 = factories.core.VendorFactory.create()
        vendor2 = factories.core.VendorFactory.create()
        offer1 = factories.core.OfferFactory.create(product=product, vendor=vendor1, unit_price=1)
        offer2 = factories.core.OfferFactory.create(product=product, vendor=vendor2, unit_price=10)
        offer21 = factories.core.OfferFactory.create(product=product, vendor=vendor2, unit_price=100)

        toporder = None
        self.assertEqual(toporder.user, user)
        self.assertEqual(toporder.vendor, None)
        self.assertEqual(toporder.suborders.count(), 2)
        suborder1 = toporder.suborders.get(vendor=vendor1)
        suborder2 = toporder.suborders.get(vendor=vendor2)
        orders = (toporder, suborder1, suborder2)
        self.assertEqual(suborder1.subtotal, 1)
        self.assertLower(suborder1.total, 3)
        self.assertEqual(suborder2.subtotal, 320)
        self.assertGreater(suborder2.total, 320)
        self.assertEqual(toporder.subtotal, suborder1.subtotal + suborder2.subtotal)
        self.assertEqual(toporder.total, suborder1.total + suborder2.total)
        all(self.assertEqual(order.status, models.Order.PROCESSING) for order in orders)

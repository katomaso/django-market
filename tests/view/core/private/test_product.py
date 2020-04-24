# coding: utf-8
import random

from decimal import Decimal
from django_webtest import WebTest
from django.core.urlresolvers import reverse
from market.core import models
from tests.factories import core


class DraftTestPositive(WebTest):
    """Test positive workflows."""

    def draft_test_add_product(self):
        """Test addition of a product into Vendor.

        Subsequently make sure that the product appears in 'products' view
        even with added category.
        """
        email = "new@user.cz"
        user, _ = models.User.objects.get_or_create_verified(email=email, name="New User")
        category = core.CategoryFactory.create()
        vendor = core.VendorFactory.create(user=user, category=category)
        page = self.app.get(reverse('admin-product-add'), user=email)
        template = {
            "name": "Product1",
            "description": "Hello, how are you?",
            "unit_price": "5000.00",
        }
        page.form['name'] = template['name']
        page.form['description'] = template['description']
        page.form['unit_price'] = template['unit_price']
        page.form['category_1'] = category.id
        response = page.form.submit()
        self.assertRedirect(response, reverse('admin-home'))
        product = models.Product.objects.get(name=template['name'])
        offer = models.Offer.objects.filter(product=product)

        self.assertEqual(product.name, template['name'])
        self.assertEqual(product.category, template['category1'])
        self.assertEqual(product.description, template['description'])
        self.assertEqual(product.unit_price, Decimal(template['unit_price']))

        self.assertEqual(product.vendor, vendor)
        self.assertEqual(offer.vendor, vendor)

        self.assertTrue(offer.unit_price == product.unit_price)
        self.assertTrue(product.active)
        self.assertTrue(offer.active)

        self.assertIn(
            product, self.app.get(reverse('products')).context['object_list'])
        self.assertIn(
            product, self.app.get(reverse('products', rest=category.slug)).context['object_list'])

# coding: utf-8
import re
import logging
import random

from django_webtest import WebTest
from django.core.urlresolvers import reverse
from django.core import mail

from market.core import models
from tests.factories import core as factory

logger = logging.getLogger(__name__)
re_link = re.compile(r'(https?\://[^\s<>\(\)\'",\|]+)')


class TestUser(WebTest):
    """Basic test of availability of registration."""

    def test_registration_without_user(self):
        """Fresh registration should lead to unverified user with a vendor."""
        self.fail("Unimplemented")

    def test_registration_unverified_user(self):
        """Unverified user should end up with the same vendor as new user."""
        email = "unverified@example.com"
        user = models.User.objects.create_user(email=email, password="password")

    def test_registration_verified_user_no_ID(self):
        """Test basic vendor registration flow.

        - user can register with and without business ID
        """
        email = "vendor@example.com"
        user = models.User.objects.create_verified_user(email=email, password="password")
        category = random.choice(models.Category.objects.filter(parent__isnull=True))
        webform = self.app.get(reverse('admin-vendor'), user=email).form
        mail.outbox.clear()
        vendor_template = {
            'name': "My Vendor",
            'motto': "We sell responsible products",
            'category': category.id,
            'description': "Locally produced without harmful chemicals.",
        }

        address_template = {
            'street': "",  # vesnican
            'city': "Louňovice 15",
            'country': "Praha-východ",
            'business_id': "",
            'tax_id': "",
        }

        webform['vendor-name'] = vendor_template['name']
        webform['vendor-motto'] = vendor_template['motto']
        webform['vendor-category_1'] = vendor_template['category']
        webform['vendor-description'] = vendor_template['description']

        for key, value in address_template.items():
            webform["address-" + key] = value

        form_response = webform.submit()

        self.assertRedirects(form_response, reverse("admin-home"))
        # now we should have a vendor without business ID
        # that means they will not pay VAT but cannot provide goods for more
        # than 20 000CZK a year according to the law
        # Should redirect to newly created vendor
        self.assertTrue(models.Vendor.objects.filter(user=user, active=True).exists())

        # the vendorper should receive email about the rules of non-legal vendor
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_verified_user_with_ID(self):
        """Test basic vendor registration flow.

        - user can register with and without business ID
        """
        email = "vendor@example.com"
        user = models.User.objects.create_verified_user(email=email, password="password")
        address = factory.Address.create(  # make sure person has no business ID
            user_shipping=user, business_id="91283464", tax_id="CZ91283464")
        category = random.choice(models.Category.objects.filter(parent__isnull=True))
        webform = self.app.get(reverse('admin-vendor'), user=email).form
        mail.outbox.clear()

        vendor_template = {
            'name': "My Vendor",
            'motto': "We sell responsible products",
            'category': category.id,
            'description': "Locally produced without harmful chemicals.",
        }

        webform['vendor-name'] = vendor_template['name']
        webform['vendor-motto'] = vendor_template['motto']
        webform['vendor-category_1'] = vendor_template['category']
        webform['vendor-description'] = vendor_template['description']
        # address form will be auto-filled from user's address
        form_response = webform.submit()

        self.assertRedirects(form_response, reverse("admin-home"))
        self.assertTrue(models.Vendor.objects.filter(user=user, active=True).exists())

        # no email necessary (user is verified)
        self.assertEqual(len(mail.outbox), 0)

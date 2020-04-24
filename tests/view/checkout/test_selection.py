"""Test cases.

Placing order as:
 - anonymous user with new unique email
 - anonymous user with known unvalidated email
 - anonymous user with known validated email and correct password
 - anonymous user with known validated email and incorrect password
 - authenticated user with validated email
 - authenticated user with unvalidated email
"""

from tests import factories
from tests.view import utils

from django_webtest import WebTest
from django.core.urlresolvers import reverse
from market.checkout import models, utils
from market.core import models as core_models


class AnynomouseUserTest(WebTest):
    """Test that anonymous user can put wares in the cart and check out."""
    csrf_checks = False

    def test_failing_name(self):
        """Test whole checkout flow.

        - is able to add wares in the cart
        - can go to checkout
        - if he forgets any of the required information he will be stopped
        - can checkout without business or tax id
        """
        email = "mr@co.uk"
        product = factories.core.ProductFactory.create()
        vendor1 = factories.core.VendorFactory.create()
        vendor2 = factories.core.VendorFactory.create()
        offer1 = factories.core.OfferFactory.create(product=product, vendor=vendor1, unit_price=1)
        offer2 = factories.core.OfferFactory.create(product=product, vendor=vendor2, unit_price=10)
        offer21 = factories.core.OfferFactory.create(product=product, vendor=vendor2, unit_price=100)

        self.assertEqual(models.Cart.objects.all().count(), 0)
        self.app.post(reverse("cart-put"),
                      params=[("pk", offer1.id), ("quantity", 1)])
        self.app.post(reverse("cart-put"),
                      params=[("pk", offer2.id), ("quantity", 2)])
        self.app.post(reverse("cart", kwargs={'action': 'put'}),
                      params=[("pk", offer21.id), ("quantity", 3)])
        self.assertGreater(models.Cart.objects.all().count(), 1)
        self.assertEqual(models.Order.objects.all().count(), 0)

        webform = self.app.get(reverse("checkout-selection")).form
        form_data = {
            'email': email,
            'necessary': '1',  # marks if address is necessary
            'billing-name': "Me Own",
            'billing-street': "My Street 123",
            'billing-city': "My City",
            'billing-zip_code': "12345",
        }
        # try empty form (email is the only mandatory field)
        response = webform.submit()
        self.assertTrue('email' in response.context['email_form'].errors)
        # try omit name
        response = utils.fill_form(webform, form_data, leave_out="billing-name").submit()
        self.assertTrue('name' in response.context['addresses_form'].billing.errors)
        # try omit email
        response = utils.fill_form(webform, form_data, leave_out="email").submit()
        self.assertTrue('email' in response.context['email_form'].errors)
        # fill in all required information
        response = utils.fill_form(webform, form_data).submit().maybe_follow()
        # a new user should be created
        user = core_models.User.objects.get(email=form_data['email'])
        # correct order should be saved in response
        request_order = utils.get_order_from_request(response.request)
        self.assertEqual(request_order.user, user)
        self.assertTrue(models.Order.objects.filter(user=user).exists())
        # continue by selecting pay-on-delivery
        response = response.click(linkid="selection-submit")
        # now we should have properly created Orders
        toporder = utils.get_order_from_request(response.request)
        suborder1 = toporder.suborders.get(vendor=vendor1)
        suborder2 = toporder.suborders.get(vendor=vendor2)
        orders = (toporder, suborder1, suborder2)
        all(self.assertEqual(order.status, models.Order.PROCESSING) for order in orders)
        # we continue

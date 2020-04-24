from decimal import Decimal
from django.core import mail
from django.shortcuts import reverse
from django_webtest import WebTest
from monthdelta import monthdelta
from market.tariff import models
from market.core import models as core_models

from tests import factories


def first(seq):
    """Return first item from a sequence."""
    if isinstance(seq, (list, tuple)):
        return seq[0]
    return next(seq)


def field_in_form(fieldname, forms):
    """Return form containing field `field_name`."""
    for key, form in forms.items():
        if fieldname in form.fields:
            return form
    # raise a helpful exception
    raise KeyError("No form with field {}! Available forms {} -> {}".format(
        fieldname,
        forms,
        "; ".join("{} -> {!s}".format(key, form.fields) for key, form in forms.items()))
    )


class TestCampaigns(WebTest):
    """Test right changing of tariffs."""

    def test_promo_code(self):
        """New vendor has to have zero-tariff assigned and progress with price/products."""
        user = core_models.User.objects.create_verified_user(
            email='email@example.com', password='hello')
        vendor = factories.core.VendorFactory.create(user=user)
        self.assertEqual(models.Billing.objects.get(vendor=vendor).tariff.daily, 0)

        current_tariff, next_tariff = tuple(
            models.Tariff.objects.filter(active=True).order_by('daily'))[:2]
        mail.outbox.clear()
        factories.core.OfferFactory.create(
            vendor=vendor, unit_price=current_tariff.price * Decimal('1.2'))
        self.assertGreaterEqual(len(mail.outbox), 1, "Change of tariff triggers an email")
        billing = models.Billing.objects.get(vendor=vendor)
        self.assertGreater(billing.tariff.daily, 0,
                           "The tariff should be non-zero because we exceeded price threshold")

        response = self.app.get(reverse("tariff-manage"), user=user.email)
        form = field_in_form("code", response.forms)

        form['code'] = 'PRVNI50'
        response = form.submit()
        # Now test whether the discount really works
        # First we need to move Billing and Statistics back to
        statistics = models.Statistics.objects.current(vendor)
        fake_start = billing.last_billed - monthdelta(billing.period)
        billing.last_billed = fake_start
        statistics.created = fake_start
        billing.save()
        statistics.save()

        # We should simulate ``bill`` management command but since it
        # only calls ``billing.bill()`` we can call it directly here.
        mail.outbox.clear()
        bill = billing.bill()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(bill.total, 0)
        self.assertEqual(models.Bill.objects.get(vendor=vendor).total, 0)

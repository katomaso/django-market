# coding: utf-8
from __future__ import absolute_import

import random
import logging
from decimal import Decimal
from datetime import timedelta
from monthdelta import monthdelta

from django import test
from django.core import mail
from django.utils import timezone
from market.core.models import User, Vendor, Address, BankAccount, Category  # Offer, Product
from market.tariff.models import Statistics, Billing, Tariff, Discount

from ..core import load as load_core
from . import load as load_tariff

logger = logging.getLogger(__name__)


def print_email():
    """Visual check of emails."""
    for email in mail.outbox:
        logger.debug(email.subject)
        logger.debug(email.body)
    mail.outbox.clear()


class TestBilling(test.TestCase):
    """Test billing behaviour when adding/removing Offers."""

    def setUp(self):
        """Create default owner of a vendor."""
        load_tariff()
        load_core()
        self.user = User.objects.get_or_create(
            email="obchodnik@prvni.cz", defaults=dict(password="hello", is_active=True))[0]
        self.address = Address.objects.get_or_create(
            user_shipping=self.user, user_billing=self.user,
            defaults=dict(street="Nova 123", city="Krno"))[0]
        self.bank_account = BankAccount.objects.get_or_create(
            number=78987658, defaults={"bank": 5388})[0]

    def tearDown(self):
        """Tidy up."""
        pass  # db gets reverted anyway

    def _create_vendor_and_stats(self):
        """Create vendor with one Statistics and shifted Billing."""
        vendor = Vendor.objects.create(
            user=self.user, bank_account=self.bank_account, address=self.address,
            name="Hello Vendor", motto="Greetings everyone",
            category=random.choice(Category.objects.all()))
        billing = Billing.objects.get(vendor=vendor)
        billing.last_billed = timezone.now().date() - monthdelta(billing.period + 1)
        billing.save()
        # create one Statistics object for the whole period
        stat = Statistics(vendor=vendor, quantity=5, price=5,
                          tariff=Tariff.objects.get(daily=Decimal("1.15")))
        stat.save()
        stat.created = timezone.now() - monthdelta(billing.period + 2)
        stat.save()
        return vendor, billing, stat

    def test_vendor_billing(self):
        """Basic test to see whether billing works in time."""
        mail.outbox = []
        vendor = Vendor.objects.create(
            user=self.user, bank_account=self.bank_account, address=self.address,
            name="Hello Vendor", motto="Greetings everyone",
            category=random.choice(Category.objects.all()))
        # there is no mail sent when creating a vendor - only adding wares and change of tariff
        self.assertEqual(len(mail.outbox), 0)
        # every vendor has to have a billing object
        self.assertTrue(Billing.objects.filter(vendor=vendor).exists())
        # every vendor has to have statistics about its usage of resources
        self.assertTrue(Statistics.objects.filter(vendor=vendor).exists())
        # build up fake statistics
        # lowest tariff assigned way before billing period
        stat = Statistics(vendor=vendor, quantity=5, price=5,
                          tariff=Tariff.objects.get(daily=Decimal("1.15")))
        stat.save()
        stat.created = timezone.now() - monthdelta(2)
        stat.save()
        self.assertEqual(Statistics.objects.filter(vendor=vendor).count(), 2)
        # add one extra expensive the same day but before the true following one
        stat = Statistics(vendor=vendor, quantity=1000, price=1000000,
                          tariff=Tariff.objects.get(daily=Decimal("70")))
        stat.save()
        stat.created = timezone.now() - timedelta(days=15, minutes=2)
        stat.save()
        # one change in the middle of billing period
        stat = Statistics(vendor=vendor, quantity=11, price=11,
                          tariff=Tariff.objects.get(daily=Decimal("2.5")))
        stat.save()
        stat.created = timezone.now() - timedelta(days=15)
        stat.save()
        # check if there are 3 artificial and 1 natural Statistics object
        self.assertEqual(Statistics.objects.filter(vendor=vendor).count(), 4)
        # force billing
        billing = Billing.objects.filter(vendor=vendor).get()
        # set the billing period as the application would - by next period
        billing.next_period = 1
        # ok, have to force it
        billing.period = 1
        billing.last_billed = timezone.now().date() - monthdelta(1)
        billing.save()
        bill = billing.bill()
        # check the correct price (make it a range bcs every month has diff #days)
        self.assertGreater(bill.total, 14 * 1.15 + 14 * 2.5)
        self.assertGreater(17 * 1.15 + 14 * 2.5, bill.total)
        # there has to be an email with billing sent
        self.assertEquals(len(mail.outbox), 1)
        mail.outbox = []
        # the bill should be for 0 CZK because this vendor has no items
        self.assertEquals(2, len(bill.items.all()))

    def test_vendor_billing_late(self):
        """Basic test to see whether billing works after period (in case of cron's crash)."""
        mail.outbox = []
        vendor, billing, stat = self._create_vendor_and_stats()
        # force late billing
        bill = billing.bill()
        # test if the quarterly billing isreally the default one
        self.assertEquals(billing.last_billed, timezone.now().date() - monthdelta(1))
        self.assertGreater(bill.total, 1.15 * 88)
        self.assertGreater(1.15 * 93, bill.total)

        # billing period of 90 days started 110 days ago
        self.assertEquals(bill.date_issuance, timezone.now().date())

    def test_vendor_closing(self):
        """Test closing a billing."""
        mail.outbox = []
        vendor, billing, stat = self._create_vendor_and_stats()
        # shift the next billing to the future
        billing.last_billed = timezone.now().date() - timedelta(days=10)
        billing.save()
        with self.assertRaises(ValueError):
            billing.bill()
        # if we bill before the end of the period we want to close the billing instead
        bill = billing.close()
        billing = Billing.objects.get(vendor=vendor)
        # test if there are some tariffs
        self.assertAlmostEquals(bill.total, stat.tariff.daily * 10, places=0)
        billing.last_billed = timezone.now().date()
        self.assertEquals(billing.active, False)

    def test_discount_wont_burn_on_free_tariffs(self):
        """Test that free tariff won't burn discounts usages."""
        mail.outbox = []
        vendor, billing, stat = self._create_vendor_and_stats()
        Statistics.objects.filter(vendor=vendor, quantity=5)\
                          .update(quantity=2, price=2,
                                  tariff=Tariff.objects.get(daily=Decimal("0")))
        Discount.objects.create(vendor=vendor, usages=1, name="Sleva")
        billing.bill()
        discount = Discount.objects.get(vendor=vendor)
        self.assertEqual(discount.usages, 1)

    def test_full_discount(self):
        """Test full discount discount."""
        mail.outbox = []
        vendor, billing, stat = self._create_vendor_and_stats()

        Discount.objects.create(vendor=vendor, usages=billing.period, percent=100, name="zdarma")
        bill = billing.bill()
        discount = Discount.objects.get(vendor=vendor)
        # check usages are equal to period (because we had 2times period at the beginning)
        self.assertEqual(discount.usages, 0)
        self.assertEquals(0, bill.total)
        # discount has to be negative
        self.assertEquals(bill.items.filter(unit_price__lt=0).count(), billing.period)

    def test_few_discounts(self):
        """Test full discount discount."""
        mail.outbox = []
        vendor, billing, stat = self._create_vendor_and_stats()
        last_month_total = stat.tariff.total(
            billing.next_billing - monthdelta(1), billing.next_billing)

        Discount.objects.create(vendor=vendor, usages=billing.period - 1, percent=100, name="zdarma")
        bill = billing.bill()
        discount = Discount.objects.get(vendor=vendor)
        # check usages are equal to period (because we had 2times period at the beginning)
        self.assertEqual(discount.usages, 0)
        self.assertGreater(bill.total, 0)
        self.assertEquals(bill.total, last_month_total)
        # discount has to be negative
        self.assertEquals(bill.items.filter(unit_price__lt=0).count(), billing.period - 1)

    def test_discount_usage_greater_than_months(self):
        """Test a discount coupon when usage is greater than billing period."""
        mail.outbox = []
        vendor, billing, stat = self._create_vendor_and_stats()
        total = stat.tariff.total(billing.last_billed, billing.next_billing)

        Discount.objects.create(vendor=vendor, usages=billing.period * 2, percent=50, name="50% sleva")
        bill = billing.bill()
        discount = Discount.objects.get(vendor=vendor)
        # check usages are equal to period (because we had 2times period at the beginning)
        self.assertEqual(discount.usages, billing.period)
        self.assertAlmostEquals(total * Decimal("0.50"), bill.total, places=0)
        self.assertEqual(bill.items.filter(unit_price__lt=0).count(), billing.period)

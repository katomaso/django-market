# coding: utf-8
from __future__ import print_function

import random
import logging


from django import test
from django.core import mail
from market.core.models import User, Vendor, Offer, Product, Address, BankAccount, Category
from market.tariff.models import Billing, Statistics, Tariff  # Bill, Discount

from ..core import load as load_core
from ..tariff import load as load_tariff


logger = logging.getLogger(__name__)

seq = iter(range(1000))


def create_offer(vendor, price):
    """Create random offer with fixed price for a fixed vendor."""
    pid = next(seq)
    p = Product.objects.get_or_create(vendor=vendor, name="product{}".format(pid), active=True,
                                      category=random.choice(Category.objects.all()),
                                      description="")[0]
    o = Offer.objects.create(vendor=vendor, product=p, active=True, unit_price=price)
    return p, o


def print_email():
    """Visual check of emails."""
    for email in mail.outbox:
        logger.debug(email.subject)
        logger.debug(email.body)
    mail.outbox = []


def print_bill(bill):
    """Visual check of bills."""
    for i in bill.items.all():
        logger.debug(i.description, i.unit_price)
    logger.debug("Total: ", bill.total())
    logger.debug("")


class TestTariffSwitching(test.TestCase):
    """Test tariff behaviour when adding/removing Offers."""

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

    def test_tariff_change(self):
        """Test tariff change with respect to change of Offers."""
        self.assertGreater(Tariff.objects.all().count(), 0)  # test if there are some tariffs
        vendor = Vendor.objects.create(
            user=self.user, bank_account=self.bank_account, address=self.address,
            name="Hello Vendor", motto="Greetings everyone",
            category=random.choice(Category.objects.all()))

        self.assertTrue(Billing.objects.filter(vendor=vendor).exists())
        qs = Statistics.objects.filter(vendor=vendor)
        self.assertTrue(qs.exists())
        stat = qs.latest("created")
        self.assertEqual(stat.tariff.daily, 0)  # the right tariff was chosen

        thresholds = Tariff.objects.all().order_by("quantity")[:4]
        offers = []
        # start adding offers - top-up tariff
        q = 0
        for tariff in thresholds:
            while q <= tariff.quantity:
                stat = qs.latest("created")
                # check the equivalence before creating an offer (might change the state)
                self.assertEqual(stat.tariff, tariff)
                self.assertEqual(stat.quantity, q)
                # price=1 because we are testing quantity not price
                offers.append(create_offer(vendor, price=1))
                q += 1
                self.assertEqual(Statistics.objects.filter(vendor=vendor).count(), q + 1)
            stat = qs.latest("created")
            # the tariff has to change
            self.assertNotEqual(stat.tariff, tariff)
            # offers has to be greater than previous threshold
            self.assertGreater(q, tariff.quantity)
            self.assertEqual(q, stat.quantity)
            # offers has to be equal than newly selected tariffs threshold
            self.assertGreater(stat.tariff.quantity, len(offers))
            # check that an email about the change was sent
            self.assertEqual(len(mail.outbox), 1)
            # check we send the new price in the email
            self.assertIn(str(stat.tariff.monthly), mail.outbox[0].body)
            mail.outbox = []

        # test lowering the tariffs
        q = len(offers)
        nstat = q + 1
        self.assertEqual(qs.count(), nstat)
        stat = qs.latest("created")
        thresholds = [stat.tariff] + list(Tariff.objects
                                          .filter(quantity__lt=stat.tariff.quantity)
                                          .order_by("-quantity"))
        for current_tariff, next_tariff in zip(thresholds, thresholds[1:]):
            # check if the tariff equality holds
            self.assertEqual(current_tariff, stat.tariff)
            # check if the following tarrif is really lower (just a sanity check)
            self.assertTrue(current_tariff.quantity > next_tariff.quantity)
            # delete offers until the tariff should change
            while q > next_tariff.quantity:
                stat = qs.latest("created")
                # no change of tariff
                self.assertEqual(stat.quantity, q)
                self.assertEqual(current_tariff, stat.tariff)
                product, offer = offers.pop()
                offer.delete()
                q -= 1
                nstat += 1
                self.assertEqual(Statistics.objects.filter(vendor=vendor).count(), nstat)
            stat = qs.latest("created")
            # the tariff has to change down
            self.assertNotEqual(current_tariff, stat.tariff)
            # the right one was selected
            self.assertEqual(next_tariff.quantity, q)
            # the new tarrif is lower than the previous one
            self.assertGreater(current_tariff.daily, next_tariff.daily)
            # the actual tariff has always greater quantity than is current quantity of Offers
            self.assertEqual(stat.tariff.quantity, q)
            # visual check of the email
            self.assertEqual(len(mail.outbox), 1)
            # check we send the new price in the email
            self.assertIn(str(stat.tariff.monthly), mail.outbox[0].body)
            mail.outbox = []

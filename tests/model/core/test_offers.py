# coding: utf-8
import random
from django import test
from market.core.models import User, Vendor, Offer, Product, Address, BankAccount, Category

from . import load as load_core
from ..tariff import load as load_tariff


def create_offer(vendor, product=None, price=None):
    """Create random offer for a given vendor and optionaly given product and price."""
    pid = random.randint(1, 9999999)
    if product is None:
        product = Product.objects.get_or_create(
            vendor=vendor, name="product{}".format(pid), description="",
            active=True, category=random.choice(Category.objects.all()))[0]
    o = Offer.objects.create(vendor=vendor, product=product, active=True,
                             unit_price=price or random.randint(2000, 100000))
    return product, o


class TestOffer(test.TestCase):
    """Test mingling with offers to one product."""

    def setUp(self):
        """Create necessary things for a vendor."""
        load_tariff()
        load_core()
        self.user = User.objects.get_or_create(
            email="obchodnik@prvni.cz", defaults=dict(password="hello", is_active=True))[0]
        self.address = Address.objects.get_or_create(
            user_shipping=self.user, user_billing=self.user,
            defaults=dict(street="Nova 123", city="Krno", name="Ondra"))[0]
        self.bank_account = BankAccount.objects.get_or_create(
            number=78987658, defaults={"bank": 5388})[0]

    def tearDown(self):
        """Tidy up."""
        self.bank_account.delete()
        self.address.delete()
        self.user.delete()

    def test_deletion(self):
        """Test properties of a product when changing offers."""
        vendor = Vendor.objects.create(
            user=self.user, bank_account=self.bank_account, address=self.address,
            name="Hello Vendor", motto="Greetings everyone",
            category=random.choice(Category.objects.all()))
        p, o = create_offer(vendor)
        o.delete()
        self.assertEqual(vendor.product_set.count(), 0)  # the product has to be deleted as well
        p, o1 = create_offer(vendor)
        p, o2 = create_offer(vendor, p)
        o1.delete()
        self.assertEqual(vendor.product_set.count(), 1)  # the product has to stay this time
        o2.delete()
        self.assertEqual(vendor.product_set.count(), 0)  # the product has to be deleted as well

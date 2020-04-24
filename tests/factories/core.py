# coding: utf-8
import factory
import string

from factory.django import DjangoModelFactory
from market.core import models


class UserFactory(DjangoModelFactory):
    """Dynamic User model."""

    class Meta:
        """Set real backend model."""
        model = models.User

    name = factory.Faker("name")
    email = factory.Iterator(
        string.ascii_lowercase,  # cycle=True by default
        getter=lambda l: "pan@{}.cz".format(l))
User = UserFactory


class AddressFactory(DjangoModelFactory):
    """Dynamic Address model."""

    class Meta:
        """Set real backend model."""
        model = models.Address

    user_billing = factory.SubFactory(UserFactory)
    user_shipping = factory.LazyAttribute(lambda this: this.user_billing)
    name = factory.Faker("name")
    street = factory.Faker("street_address")
    city = factory.Faker("city")
    zip_code = factory.Faker("postcode")
    business_id = factory.Faker("pystr", max_chars=10)
    tax_id = factory.LazyAttribute(lambda this: "CZ" + this.business_id)
Address = AddressFactory


class CategoryFactory(DjangoModelFactory):
    """Dynamic Category model without parent-child possibility now."""

    class Meta:
        """Set real backend model."""
        model = models.Category

    name = factory.Faker("color_name")
    parent = None
Category = CategoryFactory


class VendorFactory(DjangoModelFactory):
    """Dynamic Vendor model."""

    class Meta:
        """Set real backend model."""
        model = models.Vendor

    user = factory.SubFactory(UserFactory)
    address = factory.SubFactory(AddressFactory)
Vendor = VendorFactory


class ProductFactory(DjangoModelFactory):
    """Dynamic Product model."""

    class Meta:
        """Set real backend model."""
        model = models.Product

    name = factory.Faker("job")
    vendor = factory.SubFactory(VendorFactory)
    category = factory.SubFactory(CategoryFactory)
    tax = factory.Faker("pydecimal", left_digits=1, right_digits=0, positive=True)
Product = ProductFactory


class OfferFactory(DjangoModelFactory):
    """Dynamic Offer model."""

    class Meta:
        """Set real backend model."""
        model = models.Offer

    product = factory.SubFactory(ProductFactory)
    name = factory.LazyAttribute(lambda this: this.product.name)
    unit_price = factory.Faker("pyint")
    vendor = factory.SubFactory(VendorFactory)
    active = True
Offer = OfferFactory

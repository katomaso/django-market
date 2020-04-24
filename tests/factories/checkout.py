# coding: utf-8
import factory

from factory.django import DjangoModelFactory
from market.checkout import models

from . import core


class CartFactory(DjangoModelFactory):
    """Dynamic Cart model."""

    class Meta:
        """Set real backend model."""
        model = models.Cart

    user = factory.SubFactory(core.UserFactory)

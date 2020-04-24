# coding: utf-8
import importlib
import random

from .. import MockApp


def load():
    """Load tariffs from migrations to mitigate real DB."""
    from market.core.models import (
        Address, BankAccount, Vendor, Category, User, Product, Offer)
    from dbmail.models import MailTemplate
    mock_app = MockApp({
        ("core", "Product"): Product,
        ("core", "Offer"): Offer,
        ("core", "Address"): Address,
        ("core", "BankAccount"): BankAccount,
        ("core", "Vendor"): Vendor,
        ("core", "Category"): Category,
        ("core", "User"): User,
        ("dbmail", "MailTemplate"): MailTemplate
    })

    init_data = importlib.import_module('market.core.migrations.0005_initial_data')

    init_data.user_forward(mock_app, None)
    init_data.country_forward(mock_app, None)
    init_data.category_forward(mock_app, None)
    init_data.mail_forward(mock_app, None)
    init_data.core_forward(mock_app, None)


def create_categories():
    """Create few senseless categories to test."""
    from market.core.models import Category
    for category in ("parent1", "parent2", "parent3"):
        Category.objects.create(name=category, parent=None)
    for category in ("child1", "child2", "child3"):
        Category.objects.create(name=category, parent=random.choice(Category.objects.all()))

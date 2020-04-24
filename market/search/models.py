# coding: utf-8
from django.conf import settings
from django.db import models
from django.db.models import signals
from django import dispatch
from pg_fts.fields import TSVectorField
from market.core import models as core_models


class VendorSearch(models.Model):
    """Model pointing to the original searched model."""

    link = models.OneToOneField('market.Vendor', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    motto = models.CharField(max_length=255)
    description = models.TextField(null=True)

    fts_name = TSVectorField(('name', ), dictionary=settings.PG_FT_LANGUAGE)
    fts = TSVectorField(
        (('name', 'A'), ('motto', 'B'), ('description', 'C')),
        dictionary=settings.PG_FT_LANGUAGE
    )

    class Meta:
        """Define mandatory app_label."""
        app_label = 'search'
        required_db_vendor = 'postgresql'
        required_db_features = ['tsearch2']


@dispatch.receiver(signals.post_save, sender=core_models.Vendor)
def update_vendor(sender, instance, raw, created, using, update_fields, **kwargs):
    """Sync search fields with original model."""
    pass


class ProductSearch(models.Model):
    """Model pointing to the original searched model."""

    link = models.OneToOneField('market.Product', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()
    extra = models.TextField(null=True)

    fts_name = TSVectorField(('name', ), dictionary=settings.PG_FT_LANGUAGE)
    fts = TSVectorField(
        (('name', 'A'), ('description', 'B'), ('extra', 'D')),
        dictionary=settings.PG_FT_LANGUAGE
    )

    class Meta:
        """Define mandatory app_label."""
        app_label = 'search'
        required_db_vendor = 'postgresql'
        required_db_features = ['tsearch2']


class ManufacturerSearch(models.Model):
    """Model pointing to the original searched model."""

    link = models.OneToOneField('market.Manufacturer', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    fts_name = TSVectorField(('name', ), dictionary=settings.PG_FT_LANGUAGE)
    fts = TSVectorField(
        (('name', 'A'), ('description', 'B')),
        dictionary=settings.PG_FT_LANGUAGE
    )

    class Meta:
        """Define mandatory app_label."""
        app_label = 'search'
        required_db_vendor = 'postgresql'
        required_db_features = ['tsearch2']

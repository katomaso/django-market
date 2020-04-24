from __future__ import print_function
import os
import random
import re
from decimal import Decimal

from django.apps import apps
from django.db import models
from django.db.models.fields import DecimalField
from django.core.validators import RegexValidator
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import slugify

from django_comments.models import Comment

from market.utils.widgets import CurrencyInput

from . import perfect_hash


def model(name):
    """Return model class based on its (dotted) `name`."""
    if "." in name:
        return apps.get_model(name)
    return apps.get_model("market", name)


class CurrencyField(DecimalField):
    """A CurrencyField is DecimalField with max_digits=30, decimal_places=2 and value of 0.00."""

    def __init__(self, **kwargs):
        """Enforce default arguments on DecimalField."""
        defaults = {
            'max_digits': 30,
            'decimal_places': 2,  # case of bitcoin
            'default': Decimal('0.0'),
        }
        defaults.update(kwargs)
        self.widget = CurrencyInput(attrs={"class": "input-small"})
        super(CurrencyField, self).__init__(**defaults)


def slugify_uniquely(klass, name):
    """Create unique slug for `klass` from `name` by adding numbers if necessary."""
    original_slug = slugify(name)
    slug = original_slug

    if not klass.objects.filter(slug=original_slug).exists():
        return original_slug

    while True:
        i = random.randint(1, 5000)
        if klass.objects.filter(slug=slug).exists():
            slug = original_slug + str(i)
        else:
            return slug


def upload_to_classname(instance, filename):
    """Intended as ``upload_to`` for FileField."""
    basedir = str(instance.__class__.__name__).lower()
    ext = os.path.splitext(filename)[1]
    filename = None

    if not filename and hasattr(instance, "slug") and getattr(instance, "slug"):
        filename = getattr(instance, "slug")

    if not filename and instance.pk:
        filename = "image_" + str(instance.pk)

    if not filename:
        filename = "image_" + str(random.randint(1000, 1000000))
        while os.path.exists(os.path.join(settings.MEDIA_ROOT, basedir, filename + ext)):
            filename = "image_" + str(random.randint(1000, 1000000))

    return os.path.join(settings.MEDIA_ROOT, basedir, filename + ext)


def try_get(model, **filter):
    """Get or None."""
    try:
        return model.objects.get(**filter)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return None


class UidMixin(models.Model):
    """Add user-friendly UID to any model.

    Note that database value will be NULL upon first saving.
    """
    uid = models.SlugField(max_length=settings.MARKET_UID_LENGTH, blank=True, null=True)

    class Meta:
        """Mixin is always abstract."""
        abstract = True

    def __getattribute__(self, name):
        """Add UID value to the model when we have ID available."""
        value = super().__getattribute__(name)
        if name == "uid" and value is None and self.id:
            return perfect_hash.encode(self.id)
        return value

    def save(self, *args, **kwargs):
        """Add UID right after we obtain ID from the database."""
        defer_uid = False
        if not self.id:
            defer_uid = True
        super().save(*args, **kwargs)
        if defer_uid:
            self.uid = perfect_hash.encode(self.id)
            super().save(force_update=True, update_fields=['uid', ])


phone_re = re.compile(r'^[\+\d\s][\s0-9]{8,22}$')
phone_validator = RegexValidator(phone_re, _('Enter a valid phone number.'), 'invalid')


class CommentableMixin(models.Model):
    """This model has comments."""

    @property
    def comments(self):
        """Return list of related comments."""
        return list(Comment.objects.for_model(self))

    class Meta:
        """Mixin is abtract."""
        abstract = True

# coding:utf-8
from __future__ import division

import logging
import os
import re

from decimal import Decimal
from os import path

from django.conf import settings

from django.contrib.auth import models as auth_models
# from django.contrib.sites import models as sites_models
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.template import Template, Context
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _

from allauth.socialaccount.signals import social_account_added
from stdimage.models import StdImageField
from bitcategory.models import CategoryBase
from ratings.models import RatingCacheMixin
from ratings.handlers import RatingCacheHandler, ratings

from market.core.signals import vendor_closed
from market.core.managers import (
    CustomUserManager,
    CategoryManager,
    ActiveCategoryManager
)
from market.utils.models import UidMixin, CurrencyField, CommentableMixin
from market.utils.models import (
    slugify_uniquely, phone_validator, upload_to_classname)
from market.utils.templates import truncate
from market import locale

from django.db import models

from . import serializers

logger = logging.getLogger(__name__)


class User(UidMixin, auth_models.AbstractBaseUser, auth_models.PermissionsMixin):
    """Custom user model."""
    THUMB_SIZE = (95, 120, True)
    IMAGE_SIZE = (380, 480)

    name = models.CharField(_('Full name'), max_length=50, blank=True)
    email = models.EmailField(_('Email'), blank=False, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    phone = models.CharField(_("Phone number"), max_length=20,
                             validators=[phone_validator, ],
                             null=True, blank=True)
    karma = models.SmallIntegerField(_("Karma"), default=10, blank=True)

    avatar = StdImageField(upload_to=upload_to_classname, null=True, blank=True,
                           variations={"thumbnail": {"width": 95, "height": 120, "crop": True},
                                       "resized": {"width": 380, "height": 480}},
                           verbose_name=_("Photo"),)
    is_staff = models.BooleanField(_('staff status'), default=False,
                                   help_text=_('Controls if this user can log into site admin.'))
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    # site = models.ForeignKey('sites.Site', default=settings.SITE_ID)

    # these guys are there only for backward compatibility with 'old-style' libraries
    first_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30, null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['slug', ]

    # billing_address and shipping_address are provided via Address model

    objects = CustomUserManager()
    serializer = serializers.UserSerializer()

    class Meta:
        """Explicitely mark the app_label."""
        app_label = "market"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def save(self, *args, **kwargs):
        """Divide name into first and last name and slugify it."""
        if not self.name and (self.first_name or self.last_name):
            self.name = " ".join((self.first_name, self.last_name))
        if not self.name:
            self.set_name_from_email()
        if not self.slug and self.name:
            self.slug = slugify_uniquely(self.__class__, self.name)
        return super(User, self).save(*args, **kwargs)

    @property
    def username(self):
        """Email is the default username."""
        return self.email

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        """Full name is already stored in `self.name`."""
        return self.name

    def get_short_name(self):
        """Take first part of name which isn't a title."""
        titles = ("ing", "bc", "mgr", "phd", "rndr", "phdr", "judr", "mba")
        pieces = self.name.split(" ")
        for piece in pieces:
            if piece.strip(" .").lower() not in titles and "&" not in piece:
                return piece
        return self.name

    @cached_property
    def shipping(self):
        """Return foreign object or None."""
        try:
            return self.shipping_address
        except models.ObjectDoesNotExist:
            return None

    @cached_property
    def billing(self):
        """Return foreign object or None."""
        try:
            return self.billing_address
        except models.ObjectDoesNotExist:
            return None

    def shipping_billing(self):
        """Return tuple of objects or Nones if objects don't exist."""
        return self.shipping, self.billing

    @property
    def get_last_name(self):
        """Parse last name from full name."""
        titles = ("csc", "phd", "mba")
        try:
            for piece in reversed(self.name.split(" ")):
                if piece.strip(" .").lower() not in titles and "&" not in piece:
                    return piece
            return self.name
        except IndexError:
            return self.name

    def set_name_from_email(self):
        """Guess name from email because most of people has name.surname@email."""
        name, _ = self.email.split("@", 1)
        name = re.sub(r'\d', '', name)  # remove numbers
        if "#" in name:
            name = name[: name.find("#")]
        self.name = " ".join(part.title() for part in re.split(r'[\W_]', name) if len(part) > 1)

    @cached_property
    def primary_email(self):
        """Find primary email model."""
        from allauth.account.models import EmailAddress
        return EmailAddress.objects.get(user=self, primary=True)


class Product(CommentableMixin, RatingCacheMixin, models.Model):
    """Product here is just a detail description for Offer.

    The Offer is the real sold thing.
    """

    THUMB_SIZE = (350, 266)
    IMAGE_SIZE = (800, 600)
    EMPTY_THUMB_PATH = path.join(settings.STATIC_ROOT, "images/product-empty.png"),
    EMPTY_THUMB_URL = settings.STATIC_URL + "images/product-empty.png"

    name = models.CharField(max_length=255, verbose_name=_('Name'))
    slug = models.SlugField(verbose_name=_('Slug'), unique=True)
    active = models.BooleanField(default=True, verbose_name=_('Active'), db_index=True)
    removed = models.BooleanField(default=False, verbose_name=_('Removed'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date added'))
    modified = models.DateTimeField(auto_now=True, verbose_name=_('Last modified'))

    vendor = models.ForeignKey('market.Vendor', null=True, on_delete=models.SET_NULL)
    manufacturer = models.ForeignKey('market.Manufacturer', null=True, blank=True,
                                     verbose_name=_("Manufacturer"),
                                     on_delete=models.SET_NULL, db_index=True)
    category = models.ForeignKey('market.Category', verbose_name=_("Category"))
    photo = StdImageField(upload_to=upload_to_classname, blank=True, null=True,
                          verbose_name=_("Photo"), variations={
                              "thumbnail": {"width": THUMB_SIZE[0], "height": THUMB_SIZE[1]},
                              "resized": {"width": IMAGE_SIZE[0], "height": IMAGE_SIZE[1]}})
    description = models.TextField(_("Description of product"))
    extra = models.TextField(null=True, blank=True, verbose_name=_("Structured information"),
                             help_text=_("One information per line. Use colons. (e.g. wight: 20kg)"))
    expedition_days = models.SmallIntegerField(_("Days to expedition"), null=False, default=0,
                                               blank=True)
    price = CurrencyField(verbose_name=_('Best price'), null=True, blank=True,
                          help_text=_("The best price from all offers. Don't edit manually."))
    tax = models.DecimalField(_("Tax"), null=False, max_digits=2, decimal_places=0, blank=True,
                              default=settings.TAX, help_text=_("Tax in % (e.g. 21)."))

    sold = models.IntegerField(default=0)

    # Group are people who made an offer to this product
    editable = models.BooleanField(default=False, blank=True)  # if the group can edit this product

    objects = ActiveCategoryManager()
    serializer = serializers.ProductSerializer()

    class Meta:
        """Explicite app_label."""
        app_label = "market"

    def save(self, *args, **kwargs):
        """Infer slug and tax rate before saving."""
        if not self.slug:
            self.slug = slugify_uniquely(Product, self.name)
        if not self.tax:
            self.tax = settings.TAX
        if self.category_id is not None:
            self.offer_set.update(category=self.category)
        return super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def thumbnail_path(self):
        if not self.photo:
            return self.EMPTY_THUMB_PATH
        return self.photo.thumbnail.path

    @property
    def thumbnail_url(self):
        if not self.photo:
            return self.EMPTY_THUMB_URL
        return self.photo.thumbnail.url

    @property
    def offers(self):
        """Get list of active `Offer`s."""
        return (self.offer_set.filter(active=True)
                              .exclude(quantity=0)
                              .select_related('vendor', 'vendor__address')
                              .order_by('unit_price'))

    def update_price(self, save=True):
        """Set unit_price as the minimal price from all `Offer`s."""
        try:
            self.price = min(map(lambda x: x.price, self.offers))
        except (Offer.DoesNotExist, IndexError, ValueError):
            logger.error(u"Product {!s} has no offers!".format(self))
            self.price = 0.0
        if save:
            self.save()

    def get_name(self):
        """Return the name of this Product (provided for extensibility)."""
        return self.name

    def remove(self, save=True):
        """Set `removed` attribute instead of deleting the model."""
        self.removed = True
        self.active = False
        if save:
            self.save()


ratings.register(Product, RatingCacheHandler)


class Offer(models.Model):
    """An (price) `Offer` assigned by a `Vendor` to a `Product`."""
    UNIT_QUANTITIES = (
        ('ks', _("units")),
        ('g', _("grams")),
        ('kg', _("kilograms")),
    )

    name = models.CharField(max_length=255, verbose_name=_('Name'))
    slug = models.SlugField(verbose_name=_('Slug'), unique=True)
    active = models.BooleanField(default=False, verbose_name=_('Active'), db_index=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date added'))
    modified = models.DateTimeField(auto_now=True, verbose_name=_('Last modified'))

    unit_price = CurrencyField(verbose_name=_('Unit price'))
    unit_quantity = models.DecimalField(decimal_places=4, max_digits=12,
                                        null=False, blank=False, default=Decimal(1))
    unit_measure = models.CharField(max_length=5, null=False, blank=False, choices=UNIT_QUANTITIES, default='ks')

    vendor = models.ForeignKey('market.Vendor')
    product = models.ForeignKey('market.Product', blank=True, on_delete=models.CASCADE)
    category = models.ForeignKey('market.Category', null=True, blank=True)
    quantity = models.SmallIntegerField(_("Quantity"), null=False, default=-1,
                                        help_text=_("-1 means infinity"))

    sold = models.IntegerField(default=0)
    note = models.TextField(_("Comment your offer"), null=True, blank=True)

    shipping_price = CurrencyField(verbose_name=_("Shipping price"), blank=True, default=0)
    removed = models.BooleanField(default=False, verbose_name=_('Removed'))

    objects = ActiveCategoryManager()
    serializer = serializers.OfferSerializer()

    class Meta:
        """Meta."""
        app_label = "market"
        verbose_name = _('Offer')
        verbose_name_plural = _('Offers')

    def __str__(self):
        return u"{0} - {1!s}".format(self.product.name, self.unit_price)

    def save(self, *args, **kwargs):
        """Construct slug from product's slug and vendor slug."""
        if not self.name:
            self.name = self.product.name
        if not self.slug:
            self.slug = slugify_uniquely(
                self.__class__,
                "{0}--{1}".format(self.product.slug, self.vendor.slug or 'x'))
        if not self.category:
            self.category = self.product.category
        super(Offer, self).save(*args, **kwargs)
        self.product.update_price()

    def delete(self, *args, **kwargs):
        """Make sure there are no hanging `Product`s when `Offer`s are gone."""
        super(Offer, self).delete(*args, **kwargs)
        if self.product.offer_set.count() == 0:
            self.product.delete()

    def remove(self, save=True):
        """Deactivate the product instead of realy *deleting* of it."""
        self.active = False
        self.removed = True
        if save:
            self.save()
        if not self.product.offer_set.filter(removed=False).exists():
            self.product.remove(save)

    def hide(self, save=True):
        """Deactivate the product instead of real *deleting* of it."""
        self.active = False
        if save:
            self.save()
        if not self.product.offer_set.filter(active=True).exists():
            self.product.active = False
            self.product.save()

    def activate(self, save=True):
        """Deactivate the product instead of real *deleting* of it."""
        self.active = True
        self.product.active = True
        if save:
            self.save()
        else:
            self.product.update_price()

    @property
    def tax(self):
        """Tax depending on vendor tax liability."""
        if self.vendor.pays_tax:
            return self.unit_price * (self.product.tax / 100)
        return Decimal(0)

    @property
    def price(self):
        """Price with VAT (depending on the vendor)."""
        return self.unit_price + self.tax

    @property
    def norm_price(self):
        """Normalize `price` per ks or kg."""
        if self.unit_quantity == 'g':
            return self.price / (self.unit_measure * Decimal('0.001'))

        if self.unit_measure == 1:
            return self.price

        return self.price / self.unit_measure


class Category(CategoryBase):
    """Add decription to category."""
    description = models.TextField(null=True, blank=True)
    is_parent = models.BooleanField(default=False)
    serializer = serializers.CategorySerializer()

    class Meta(object):
        """Make owning app explicit."""
        app_label = "market"
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['ordering', 'path']

    def save(self, *args, **kwargs):
        """Cache value of `is_parent` in the model."""
        if self.parent is not None:
            if self.parent.is_parent is False:
                self.parent.is_parent = True
                self.parent.save()
        return super().save(*args, **kwargs)

    def __str__(self):
        return "{:d}: {}".format(self.id, self.name)


class Vendor(UidMixin, RatingCacheMixin, models.Model):
    """Vendor is a mandatory model for selling stuff."""

    group_name = "vendor"
    THUMB_SIZE = (300, 300, False)
    IMAGE_SIZE = (800, 600)
    BACKGROUND_SIZE = (960, 720)
    EMPTY_THUMB_PATH = path.join(settings.STATIC_ROOT, "images/vendor-empty.png"),
    EMPTY_THUMB_URL = settings.STATIC_URL + "images/vendor-empty.png"

    limit_product_count = 4
    limit_product_total = Decimal(5000)

    message = {
        "at_limit": _("Unofficial vendors cannot go beyond {:d} products or {!s} total price").format(
            limit_product_count, limit_product_total),
    }

    user = models.OneToOneField(settings.AUTH_USER_MODEL)  # Every user can have only one vendor
    name = models.CharField(
        _("Vendor name"), max_length=100, help_text=_('No need to be official or unique.'))
    motto = models.CharField(_("Motto"), max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey('market.Category', verbose_name=_("Category"), null=True, blank=False)
    description = models.TextField(_("Description of your vendor"), null=True, blank=True)
    logo = StdImageField(
        upload_to=upload_to_classname, null=True, blank=True, verbose_name=_("Photo"),
        variations={"thumbnail": {"width": THUMB_SIZE[0], "height": THUMB_SIZE[1]},
                    "resized": {"width": IMAGE_SIZE[0], "height": IMAGE_SIZE[1]}},
        help_text=_('Preferable a square of size 300x300 pixels'))
    background = StdImageField(
        upload_to=upload_to_classname, null=True, blank=True, verbose_name=_("Background"),
        variations={"resized": {"width": BACKGROUND_SIZE[0], "height": BACKGROUND_SIZE[1]}},
        help_text=_('Preferable a rectagle of size 960x720 pixels'))

    bank_account = models.OneToOneField('market.BankAccount', null=True, blank=True)
    address = models.OneToOneField('market.Address', verbose_name=_("Billing Address"), null=False)
    position = models.ForeignKey('market.Address', verbose_name=_("Placement of your vendor"),
                                 null=True, related_name="vendor_locations+")
    openings = models.TextField(_("Opening hours"), null=True, blank=True)

    active = models.BooleanField(default=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    deactivated = models.DateTimeField(null=True, blank=True)

    ships = models.BooleanField(default=True, help_text=_("You are shipping wares to customers"))

    objects = ActiveCategoryManager()
    serializer = serializers.VendorSerializer()

    class Meta:
        """Explicit label."""
        app_label = "market"

    def save(self, *args, **kwargs):
        """Construct slug if not explicitely given before saving."""
        if not self.slug:
            self.slug = slugify_uniquely(self.__class__, self.name)
        super(Vendor, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Delete image files before deleting the model."""
        try:
            if self.logo is not None:
                os.remove(self.logo.thumbnail.path())
                os.remove(self.logo)
        except:
            logger.error("Could not remove all images")
        return super(Vendor, self).delete(*args, **kwargs)

    @property
    def pays_tax(self):
        """Mark if this vendor is an official vendor with tax duty."""
        return self.address.tax_id is not None

    @property
    def has_limit(self):
        """Unofficial vendors (without business id) has constraints."""
        return self.address.business_id is None

    def at_limit(self):
        """Check if the limit was reached and to disallow more actions."""
        if not self.has_limit:
            return False
        if self.offers.count() >= Vendor.limit_product_count:
            return True

        if self.total >= Vendor.limit_product_total:
            return True
        return False

    def __str__(self):
        if self.name:
            return self.name
        if self.category and self.user:
            return self.category + u" " + self.user.name
        if self.user:
            return self.user.name
        return u""

    @cached_property
    def total(self):
        """Sum of prices of all offers."""
        return self.offer_set.filter(removed=False)\
                             .aggregate(total=models.Sum('unit_price'))['total']

    def close(self):
        """Deactivate the vendor and all offers with it.

        Send a signal in the end because there might be other classes interested.
        """
        self.offer_set.update(active=False)
        for product in self.product_set.all():
            if product.offers.count() == 1:
                product.active = False
                product.save()
        self.active = False
        self.deactivated = timezone.now()
        self.save()
        vendor_closed.send(sender=self.__class__, instance=self)

    @property
    def short_description(self):
        """Extract a short description from available fields."""
        if self.motto:
            return self.motto
        return truncate(self.description, 250)

    @property
    def offers(self):
        """Active offers of the vendor."""
        return (self.offer_set.filter(active=True)
                              .select_related('product')
                              .exclude(quantity=0)
                              .order_by('-created'))

ratings.register(Vendor, RatingCacheHandler)


class Address(models.Model):
    """Address linked to users and to companies (has optional VAT ID)."""
    user_shipping = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='shipping_address',
                                         blank=True, null=True, verbose_name=_("Shipping"))
    user_billing = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='billing_address',
                                        blank=True, null=True, verbose_name=_("Billing"))

    name = models.CharField(_('Name/Company'), max_length=255, null=True, blank=False)
    street = models.CharField(_('Street'), max_length=255, null=True, blank=True)
    city = models.CharField(_('City'), max_length=20)
    zip_code = models.CharField(_('Post Code'), max_length=20, null=True, blank=False)
    state = models.CharField(_('State'), max_length=50, null=True, blank=True)
    country = models.CharField(_('Country'), max_length=10, null=False, blank=False,
                               choices=locale.get_data('countries'))
    # Once we rely on PostGIS ...
    # position = models.PointField(srid=4326, null=True, blank=True)
    position_x = models.DecimalField(_('Position lng'), null=True, blank=True,
                                     max_digits=19, decimal_places=16)
    position_y = models.DecimalField(_('Position lat'), null=True, blank=True,
                                     max_digits=19, decimal_places=16)
    business_id = models.CharField(_("Business number"), max_length=10, null=True, blank=True)
    tax_id = models.CharField(_("Tax ID"), max_length=12, null=True, blank=True)

    extra = models.TextField(_("Further description"), null=True, blank=True,
                             help_text=_('Will appear on an invoice.'))

    class Meta:
        """Explicite market label."""
        app_label = "market"
        verbose_name = _('Address')
        verbose_name_plural = _("Addresses")

    def __str__(self):
        return u'{0} ({1}, {2})'.format(self.name, self.street, self.city)

    # def save(self, force_insert=False, force_update=False, using=None,
    #          update_fields=None):
    #     if self.position_x and self.position_y and hasattr(self, "position") and not getattr(self, "position", None):
    #         self.position = "POINT({0}, {1})".format(self.position_x, self.position_y)
    #     return super(Address, self).save(force_insert, force_update, using,update_fields)

    def clone(self):
        new_kwargs = dict([(fld.name, getattr(self, fld.name))
                           for fld in self._meta.fields if fld.name != 'id'])
        return self.__class__.objects.create(**new_kwargs)

    def as_text(self):
        """Used by invoice app."""
        return Template(settings.ADDRESS_TEMPLATE).render(Context(model_to_dict(self)))

    @property
    def lng(self):
        if getattr(self, "position", None):
            return self.position.x
        if self.position_x:
            return self.position_x
        return None

    @property
    def lat(self):
        if getattr(self, "position", None):
            return self.position.y
        if self.position_y:
            return self.position_y
        return None


class BankAccount(models.Model):
    """Bank bank_account. Mandatory for SHOP (they have user=None)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name='bank_accounts')
    prefix = models.DecimalField(_('Prefix'), null=True, blank=True,
                                 max_digits=15, decimal_places=0)
    number = models.DecimalField(_('Account number'), decimal_places=0,
                                 max_digits=16)
    bank = models.DecimalField(_('Bank code'), decimal_places=0, max_digits=4)

    class Meta:
        """Mark app_label explicitely."""
        app_label = "market"

    def __str__(self):
        if self.prefix:
            return u"{}-{}/{}".format(self.prefix, self.number, self.bank)
        return u"{}/{}".format(self.number, self.bank)

    as_text = __str__


class Manufacturer(RatingCacheMixin, models.Model):
    """Manufacturer of a product.

    Products might be sold by a salesman. Manufacturer can be created by
    salesmen and extended by the manufacturer for contact and stuff.
    """
    THUMB_SIZE = (300, 300, False)
    IMAGE_SIZE = (800, 600)

    name = models.CharField(max_length=100)
    slug = models.SlugField()
    email = models.EmailField(max_length=50, null=True, blank=True, help_text=_('Customer support'))
    phone = models.CharField(max_length=20, validators=[phone_validator, ],
                             null=True, blank=True)
    address = models.ForeignKey('market.Address', verbose_name=_("Headquaters"),
                                null=True, blank=True)
    category = models.ForeignKey('market.Category', null=True, blank=True,
                                 verbose_name=_("Manufacturer specialization"))
    description = models.TextField(_("Short description of the company"),
                                   null=True, blank=True)
    logo = StdImageField(upload_to=upload_to_classname, null=True, blank=True, verbose_name=_("Photo"),
                         variations={"thumbnail": {"width": THUMB_SIZE[0], "height": THUMB_SIZE[1]},
                                     "resized": {"width": IMAGE_SIZE[0], "height": IMAGE_SIZE[1]}},
                         help_text=_('Preferable a square of size 300x300 pixels'))

    objects = CategoryManager()

    class Meta:
        """Mark app_label explicitely."""
        app_label = "market"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Add slug if non-existing."""
        if not self.slug:
            self.slug = slugify_uniquely(self.__class__, self.name)
        return super(Manufacturer, self).save(*args, **kwargs)


ratings.register(Manufacturer, RatingCacheHandler)


@receiver(social_account_added)
def populate_user_name(request, sociallogin, **kwargs):
    if not sociallogin.account.user.name or len(sociallogin.account.user.name) < 3:
        # try to craft real name
        data = sociallogin.account.extra_data
        name = (data.get("name", "") or
                data.get("full_name", "") or
                data.get("fullname", "") or
                " ".join((data.get("first_name", ""), data.get("last_name", ""))) or
                sociallogin.account.user.name
                )
        sociallogin.account.user.name = name
        sociallogin.account.user.save()

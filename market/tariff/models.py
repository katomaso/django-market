# coding: utf-8
from __future__ import division

import logging

from copy import copy
from datetime import date, datetime
import decimal
from decimal import Decimal
from monthdelta import monthdelta, monthmod

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.db import transaction
from django.conf import settings
from django.dispatch import receiver
from django.utils import timezone
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as lazy_, ugettext as _
from django.utils.functional import cached_property

from invoice.models import Invoice
from dbmail import send_db_mail

from market.core.models import Vendor, Offer
from market.core.signals import vendor_open, vendor_closed
from market.utils import defaults
from market.utils.models import CurrencyField

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class Billing(models.Model):
    """One billing per vendor. It keeps track of their setting of billing app.

    This model stores which vendor has chosen which billing period and when the last billing was
    performed. The :method:`bill` is periodically called by an external tool.
    """

    PERIODS = (
        (1, lazy_('monthly')),
        (3, lazy_('quartely')),
        (6, lazy_('half-yearly')),
        (12, lazy_('yearly')),
    )
    DEFAULT_PERIOD = 3

    vendor = models.OneToOneField('market.Vendor')

    period = models.PositiveIntegerField(default=DEFAULT_PERIOD, choices=PERIODS)
    next_period = models.PositiveIntegerField(
        lazy_("Next billing period"), default=DEFAULT_PERIOD, choices=PERIODS)
    last_billed = models.DateField(default=timezone.now)
    next_billing = models.DateField(blank=True, help_text=lazy_('Is set automatically'))
    active = models.BooleanField(default=True, db_index=True)

    class Meta:
        """Meta class to force ordering by date."""
        app_label = "market"
        verbose_name = _("Billing")
        verbose_name_plural = _("Billings")

    def __str__(self):
        return _("{0.name} next billing {1:%d.%m.%Y}").format(self.vendor, self.next_billing)

    def save(self, *args, **kwargs):
        """Sync times on save."""
        if self.next_period != self.period:
            if timezone.now().date() in (self.last_billed, self.next_billing):
                self.period = self.next_period
                self.next_billing = self.last_billed + monthdelta(self.period)

        self.next_billing = self.last_billed + monthdelta(self.period)
        return super(Billing, self).save(*args, **kwargs)

    @cached_property
    def tariff(self):
        """Current tariff based of statistics of a vendor."""
        return Statistics.objects.current(self.vendor).tariff

    def close(self):
        """Close the vendor and issue last billing."""
        self.active = False
        self.next_billing = timezone.now().date()
        return self.bill()

    @transaction.atomic
    def bill(self):
        """
        Issue a bill for a vendor.

        This method is called periodically by an external tool. It let all duties bill up and the
        executes all price modifiers such as discount encounters.

        We have to bill the vendor at the time of call. Only when the billing happened already
        today (or in the future) we will ignore that call.

        :rvalue:`tariff.Bill` the created bill (invoice)
        """
        if self.last_billed >= timezone.now().date():
            return Bill.objects.filter(period_end=timezone.now().date()).get()

        if self.next_billing > timezone.now().date():
            raise ValueError("Can not bill before the end of billing period - close it instead.")

        contractor = defaults.vendor()
        bill = Bill.objects.create(
            vendor=self.vendor, logo=contractor.logo.path if contractor.logo else None,
            subscriber=self.vendor.address,
            period_start=self.last_billed, period_end=self.next_billing,
            contractor=contractor.address, contractor_bank=contractor.bank_account)

        months, rest = monthmod(self.last_billed, self.next_billing)
        # tranform date to datetime for billing useng StatisticsManager
        last_billed = datetime(self.last_billed.year, self.last_billed.month, self.last_billed.day)
        # bill by months (because of Discounts and better visibility on the bill)
        for month in range(months.months):
            total = Decimal("0.00")
            for tariff, price in Statistics.objects.bill(self.vendor,
                                                         last_billed + monthdelta(month),
                                                         last_billed + monthdelta(month + 1)):
                bill.add_item(tariff, price, settings.TAX)
                total += price

            discount = Discount.objects.cut_the_price(self.vendor, total)
            if discount is not None:
                bill.add_item(*discount)

        # bill the remaining time (if there is some)
        if rest.days > 1:
            total = Decimal("0.00")
            for tariff, price in Statistics.objects.bill(self.vendor,
                                                         last_billed + months,
                                                         last_billed + months + rest):
                bill.add_item(tariff, price, settings.TAX)
                total += price

            discount = Discount.objects.cut_the_price(self.vendor, total)
            if discount is not None:
                bill.add_item(*discount)

        if bill.total < 0:
            bill.add_item(_("Rounding price to zero"), -1 * bill.total)

        self.last_billed = self.next_billing

        self.save()  # periods change is taken care of in .save() method
        bill.save()
        bill.send()
        return bill


@python_2_unicode_compatible
class Tariff(models.Model):
    """Tarrif assigned to every vendor and reviewed with every change in amount of products."""

    name = models.CharField(max_length=120)
    description = models.TextField(null=True)
    slug = models.SlugField()
    daily = CurrencyField(default=0)
    active = models.BooleanField(db_index=True, default=True)
    # following fields set limits when the tariff should be used
    quantity = models.IntegerField()
    price = CurrencyField()

    class Meta:
        """Meta class to force ordering by date."""
        app_label = "market"
        verbose_name = _("Tariff")
        verbose_name_plural = _("Tariffs")
        ordering = ("daily", )

    def __str__(self):
        return self.name

    def total(self, days, end=None):
        """Return price for the tariff wrt days of usage or dates of usage."""
        if end is not None and isinstance(days, (date, datetime)):
            days = (end - days).days
        return (self.daily * Decimal(days)).to_integral_value(rounding=decimal.ROUND_HALF_UP)

    @property
    def monthly(self):
        """Return the monthly price for this tariff."""
        return (self.daily * Decimal("30")).to_integral_value(rounding=decimal.ROUND_HALF_UP)


class StatisticsManager(models.Manager):
    """Hold stats for a vendor.

    This class is used to decide for tariff assignments.
    """

    def create(self, vendor, save=True, **kwargs):
        """Precompute stats upon creation of new stats."""
        stat = Statistics(vendor=vendor)
        qs = vendor.offer_set.filter(active=True).exclude(quantity=0)
        stat.quantity = qs.count()
        stat.price = qs.aggregate(models.Sum('unit_price'))['unit_price__sum'] or Decimal(0)
        stat.tariff = Tariff.objects.filter(
            active=True, quantity__gte=stat.quantity, price__gte=stat.price).order_by("daily")[0]
        if save:
            stat.save(using=self._db)
        return stat

    def current(self, vendor):
        """Return the most recent stats (since we keep historical records)."""
        return self.get_queryset().filter(vendor=vendor).latest("created")

    def bill(self, vendor, period_start, period_end):
        """Use statistics records to select propriate tariffs.

        :return: list of tuples(<text>, price) ready to be added to a bill
        """
        prime = self.get_queryset().filter(vendor=vendor,
                                           created__lte=period_start
                                           ).latest("created")
        following = self.get_queryset().filter(vendor=vendor,
                                               created__gt=period_start,
                                               created__lte=period_end
                                               ).order_by("created")
        monthly = 0
        if following.count() == 0:
            # there was no change in Offers during the whole billing period
            monthly = prime.tariff.total(period_start, period_end)
            return [(prime.to_string(period_start, period_end), monthly)]  # price

        bill_items = []
        # we have more stats during the billing period - construct chain of changes
        periods = [(period_start, prime), ]
        prev_stat = prime
        for stat in following:
            if stat.tariff == prev_stat.tariff:
                prev_stat = stat
                continue
            if stat.created.date() == prev_stat.created.date():
                prev_stat = stat
                continue
            periods.append((stat.created, stat))
        periods.append((period_end, None))
        # account tarrifs with period longer than 1 day
        for i in range(len(periods) - 1):
            start, stat = periods[i]
            end, _ = periods[i + 1]
            if (end - start).days < 1:
                continue  # ignore period shorter than 1 day
            monthly += stat.tariff.total(start, end)
            bill_items.append((stat.to_string(start, end), stat.tariff.total(start, end)))
        return bill_items


@python_2_unicode_compatible
class Statistics(models.Model):
    """Statistics computed after addition of every :model:`core.Offer`.

    These values are the base for monthly billing. There is a foreign key
    to Tariff to keep tariffs even though they obsolete.
    """

    vendor = models.ForeignKey('market.Vendor', on_delete=models.CASCADE, null=False)
    created = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveIntegerField(null=False, default=0)
    price = CurrencyField(default=0)
    tariff = models.ForeignKey('market.Tariff')

    objects = StatisticsManager()

    class Meta:
        """Explicitely mark the app_label."""
        app_label = "market"
        verbose_name = _("Statistics")
        verbose_name_plural = _("Statistics")

    def __str__(self):
        return u"{} on {:%d.%m %Y} had {} items of value {}".format(
            str(self.vendor), self.created, self.quantity, self.price)

    def __eq__(self, other):
        if not isinstance(other, Statistics):
            return False
        return self.quantity == other.quantity and self.price == other.price

    def to_string(self, start, end):
        """Format string of usage period with tariff included."""
        return u" ".join((force_text(self.tariff), _("Used"),
                          _("from"), u"{:%d.%m %Y}".format(start),
                          _("until"), u"{:%d.%m %Y}".format(end)))


class Bill(Invoice):
    """The billing document for every closed billing period."""

    vendor = models.ForeignKey('market.Vendor')
    period_start = models.DateField()
    period_end = models.DateField()

    class Meta:
        """Force default ordering by `period_end`."""
        app_label = 'market'
        verbose_name = _("Bill")
        verbose_name_plural = _("Bills")
        ordering = ["-period_end", ]

    def send(self):
        """Send an email with proforma/invoice."""
        send_db_mail("tariff-billed", self.vendor.user.email, {'bill': self},
                     attachments=[self.export_attachment()])


class DiscountManager(models.Manager):
    """Provide complicated discount selection."""

    def cut_the_price(self, vendor, total):
        """Find the best discount for given total."""
        if total <= 0.0:
            return None
        candidate = self.get_queryset().filter(vendor=vendor, usages__gt=0)
        if candidate.exists():
            best = candidate.order_by("-percent")[0]
            return best.use(total)
        return None


@python_2_unicode_compatible
class Discount(models.Model):
    """Discount in % or abs.val with possibly many months duration."""

    name = models.CharField(max_length=120)
    percent = models.SmallIntegerField(default=100, help_text=lazy_("Discount in %"))
    usages = models.SmallIntegerField(default=1, help_text=lazy_('Usages in months'))
    vendor = models.ForeignKey('market.Vendor', related_name='tariff_discounts', null=True)

    objects = DiscountManager()

    class Meta:
        """Explicitely mark the app_label."""
        app_label = "market"
        verbose_name = _("Discount")
        verbose_name_plural = _("Discounts")

    def __str__(self):
        return "{} {:d}% {} {:d} {}.".format(
            _("Discount"), self.percent, _("for next"), self.usages, _("paid months"))

    def use(self, total):
        """Use once this discount on `total`."""
        self.usages -= 1
        self.save()
        discount = Decimal("-0.01") * self.percent * total
        return (self.name, discount.to_integral_value(), app_settings.TAX)


class Campaign(models.Model):
    """A discount code for campaigns."""

    code = models.SlugField(max_length=8, help_text=_("Has to be UPPER CASE"))
    expiration = models.DateTimeField()
    usages = models.SmallIntegerField()
    # settings of the current discount
    discount = models.ForeignKey('market.Discount')
    # keep track who used that so far
    vendors = models.ManyToManyField(Vendor)

    class Meta:
        """Explicitely mark the app_label."""
        app_label = "market"
        verbose_name = _("Campaign")
        verbose_name_plural = _("Campaigns")

    def __str__(self):
        return self.discount.name

    def use(self, vendor):
        """Use the campaign once to give the `vendor` a discount."""
        if self.vendors.filter(pk=vendor.pk).exists():
            raise ValueError(_("Vendor already has this discount"))
        self.usages -= 1
        self.vendors.add(vendor)
        discount = copy(self.discount)
        discount.pk = None
        discount.vendor = vendor
        discount.save(force_insert=True)
        self.save()

    @cached_property
    def used(self):
        return self.vendors.all().count()


#@receiver((post_save, post_delete), sender=Offer)
#def discount_to_the_first_vendors(sender, instance, **kwargs):
#    """Provide 100% discounts to the first 50 active vendor owners."""
#    if instance.vendor.tariff_discounts.exists():
#        return

#    if not instance.vendor.offers.exclude(quantity=0).exists():
#        return

#    discounts = Discount.objects.filter(percent=100, usages=3, vendor__isnull=True)
#    if discounts.exists():
#        discount = discounts.first()
#        discount.vendor = instance.vendor
#        discount.save()


@receiver((vendor_open, post_save), sender=Vendor)
def vendor_open_hook(sender, instance, created, **kwargs):
    """Every vendor has to have a Billing assigned."""
    billing, billing_created = Billing.objects.get_or_create(vendor=instance)
    if billing_created:
        Statistics.objects.create(vendor=instance)

    if not billing.active and instance.active:
        billing = Billing.objects.filter(vendor=instance).get()
        billing.active = True
        billing.last_billed = timezone.now().date()
        billing.period = (billing.next_period or billing.period)
        billing.save()


@receiver(vendor_closed, sender=Vendor)
def vendor_closed_hook(sender, instance, **kwargs):
    """Finalize Billing and Statistics for a closed vendor."""
    Billing.objects.get(vendor=instance).close()
    Statistics.objects.create(vendor=instance)
    send_db_mail('tariff-closed', instance.user.email, {"vendor": instance})


@receiver((post_save, post_delete), sender=Offer)
def offer_change_hook(sender, instance, **kwargs):
    """Update Statistics based on vendor's wares count and value."""
    prev_stats = Statistics.objects.current(instance.vendor)
    new_stats = Statistics.objects.create(instance.vendor, save=False)
    if new_stats == prev_stats:
        return
    new_stats.save()
    if prev_stats.tariff != new_stats.tariff:
        send_db_mail('tariff-changed', instance.vendor.user.email, {
            'tariff': new_stats.tariff,
            'discounts': Discount.objects.filter(vendor=instance.vendor, usages__gt=0)})

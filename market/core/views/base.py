import json
import re

from allauth import account

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from market.core import models
from market.core.views import MarketListView, MarketDetailView
from market.core.views import CategorizedMixin

from . import maps


class Home(MarketListView):
    """Home Page of the whole project."""

    ordering = '-created'

    def get_context_data(self, **kwargs):
        """Add map markers."""
        context = super().get_context_data(**kwargs)
        # add map markers here because it needs custom queryset
        maps.add_map_markers(
            context,
            models.Vendor.objects.filter(active=True, position__isnull=False),
            maps.vendor_marker
        )
        return context

    def get_context_links(self, **context):
        return {
            "self": reverse("market-home"),

        }

    def get_queryset(self):
        """Show products without specification of category."""
        return models.Product.objects.active()


class Products(CategorizedMixin, MarketListView):
    """Show products."""

    ordering = '-modified'
    marker = None  # maps.products_marker and extend maps.MappedMixin

    def get_queryset(self):
        """Show products based on selected category."""
        if self.category:
            return models.Product.objects.within(self.category)
        return models.Product.objects.all().order_by()


class Vendor(CategorizedMixin, MarketListView):
    """Detail of one vendor."""

    def dispatch(self, request, slug, *args, **kwargs):
        """Add self.vendor - a Vendor instance."""
        self.vendor = get_object_or_404(models.Vendor, slug=slug)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add vendor into context as 'object'."""
        context = super().get_context_data(**kwargs)
        context['object'] = self.vendor
        return context

    def get_queryset(self, request, *args, **kwargs):
        """Show personalised page of one vendor with solely its offers."""
        if self.category:
            return (self.vendor.offers
                    .filter(category_id__gte=self.category.gte)
                    .filter(category_id__lt=self.category.lt))
        return self.vendor.offers


class Vendors(CategorizedMixin, MarketListView):
    """Show vendors according to categories."""
    marker = None  # maps.vendor_marker

    def get_queryset(self):
        """Show vendors according to categories."""
        if self.category:
            return models.Vendor.objects.filter(
                active=True,
                category_id__gte=self.category.gte,
                category_id__lt=self.category.lt)
        return models.Vendor.objects.filter(active=True)

    def get_context_data(self, *args, **kwargs):
        """Add total vendors count."""
        context = super().get_context_data(*args, **kwargs)
        context.update(vendors_count=models.Vendor.objects.filter(active=True).count())
        return context


class Manufacturer(MarketListView):
    """Manufacturer of products."""

    def dispatch(self, request, slug, *args, **kwargs):
        """Add manufacturer into instance."""
        self.manufacturer = get_object_or_404(models.Manufacturer, slug=self.kwargs['slug'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add manufacturer as 'object' into context."""
        context = super().get_context_data(**kwargs)
        context['object'] = self.manufacturer
        return context

    def get_queryset(self):
        """Personalized site of a manufacturer."""
        return models.Product.objects.filter(manufacturer=self.manufacturer)


class Manufacturers(MarketListView):
    """List of manufacturers."""

    def get_context_data(self, **kwargs):
        """Add category to the context."""
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context

    def get_queryset(self):
        """Show list of manufacturers inside one category."""
        if self.category:
            return (models.Manufacturer.objects.exclude(description__isnull=True)
                    .filter(category_id__gte=self.category.gte)
                    .filter(category_id__lt=self.category.lt))
        return models.Manufacturer.objects.exclude(description__isnull=True)


class Product(MarketDetailView, MarketListView):
    """Show one product."""

    model = models.Product
    marker = None  # maps.product_marker

    def get_context_links(self, **kwargs):
        """Add possible links to the context."""
        links = {}
        if self.object.manufacturer is not None:
            links['manufacturer'] = self.reverse(
                "manufacturer", slug=self.object.manufacturer.slug)
        return links

    def get_queryset(self):
        """Return offers as item list."""
        return self.object.offers


def validate_email(request):
    """Check whether email is already registered.

    This is called from checkout-selection mainly. Since the checkout is
    possible without registration we need to verify email status.
    """
    data = json.parse(request.body) or request.POST
    if re.match(r"[\w\.\-_]{1,62}@[\w\.\-_]{1,62}\.\w{1,12}", data.get("email")) is None:
        return JsonResponse({'valid': False, 'exists': False})

    return JsonResponse({
        "exists": account.models.EmailAddress.objects.filter(
            email=data.get("email")).exists(),
        "valid": True})

from django.shortcuts import get_object_or_404

from urljects import url_view, U, end

from market.core.views import MarketListView
from market.core import models as core_models


@url_view(U / end, name="search")
def search_nothing(request, *args, **kwargs):
    """Mock search engine."""
    return "Nothing"


class SearchProduct(MarketListView):
    """Search engine within products.

    This concept needs rewriting.
    """

    def get_queryset(self, request, query, *args, **kwargs):
        """Search withing product names."""
        if request.GET.get("obchod"):
            vendor_id = int(request.GET.get("obchod")[0])
            vendor = get_object_or_404(core_models.Vendor, id=vendor_id)
            return vendor.offers.filter(product__fts__search=query)

        return (core_models.Product.objects
                    .active()
                    .filter(fts__search=query)
                    .order_by('-created'))

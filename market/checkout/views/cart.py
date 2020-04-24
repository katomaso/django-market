# coding: utf-8
import logging

from django.forms import ValidationError

from django.http import Http404, HttpResponseBadRequest
from django.utils.translation import ugettext as _
from django.shortcuts import redirect, get_object_or_404

from market.core.views import MarketView
from market.core import models as core_models

from .. import models
from .. import utils
from .. import forms

logger = logging.getLogger(__name__)


class Cart(MarketView):
    """User can manipulate their Cart.

    Cart is a mutable singleton object therefor there is no /cart/id API.
    """

    def get_context_data(self, **kwargs):
        """There is no get_context_data on super(), we inherit from the mixin."""
        ctx = super().get_context_data(**kwargs)
        cart = utils.get_or_create_cart(self.request)
        cart.update(self.request)
        ctx.update({'object': cart})
        return ctx

    def get(self, request, *args, **kwargs):
        """Add cart items into context."""
        context = self.get_context_data(**kwargs)
        cart = utils.get_or_create_cart(self.request)
        formset = forms.get_cart_item_formset(cart_items=cart.items)
        context.update({'formset': formset, })
        return self.render_to_response(context)

    def delete(self, *args, **kwargs):
        """Empty vendorping cart."""
        cart_object = utils.get_or_create_cart(self.request)
        cart_object.empty()
        return self.render_to_response(self.get_context_data({'object': cart_object}))

    def post(self, *args, **kwargs):
        """Update shopping cart items quantities.

        Data should be in update_item_ID=QTY form, where ID is id of cart item
        and QTY is quantity to set.
        """
        context = self.get_context_data(**kwargs)
        try:
            formset = forms.get_cart_item_formset(
                cart_items=context['cart_items'], data=self.request.POST)
        except ValidationError:
            return redirect('cart', format="html")
        if formset.is_valid():
            formset.save()
            return self.success()
        context.update({'formset': formset, })
        return self.render_to_response(context)


class CartItem(MarketView):
    """Handle CartItem-related operations."""

    def get(self, request, *args, **kwargs):
        """Simply render cart tag."""
        cart = utils.get_or_create_cart(request)
        cart.update(request)
        return self.render_to_response({'cart': cart})

    def put(self, *args, **kwargs):
        """Add a new item to the cart with optional `quantity` (defaults to 1)."""
        if self.data.get("pk"):
            item_instance = get_object_or_404(core_models.Offer,
                                              pk=int(self.data.get("pk")))
        elif self.data.get("slug"):
            item_instance = get_object_or_404(core_models.Offer,
                                              slug=self.data.get("slug"))
        else:
            logger.error("Malicious request data: " + str(self.data))
            raise Http404("Specify 'pk' or 'slug'!")

        item_quantity = int(self.data.get('quantity', 1))
        if item_quantity < 0:
            raise ValueError("Quantity has to be non-negative")

        cart_object = utils.get_or_create_cart(self.request, save=True)
        cart_object.add_item(item_instance, item_quantity, merge=True)
        return self.render_to_response({'cart': cart_object})

    def delete(self, request, *args, **kwargs):
        """Delete one of the cartItems.

        This should be posted to a properly RESTful URL (that should
        contain the item's ID): http://example.com/vendor/cart/item/12345
        """
        cart_object = utils.get_or_create_cart(self.request)
        item_id = self.kwargs.get('pk')
        try:
            cart_object.delete_item(item_id)
            return self.render_to_response({"status": "ok", "id": item_id})
        except models.Cart.ObjectDoesNotExist:
            raise Http404

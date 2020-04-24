import json

from django.contrib import messages
from django.shortcuts import redirect, reverse
from django.http import HttpResponse
from django.utils.translation import ugettext as _

from market.core.views import MarketView
from market.checkout import utils


class AjaxResponseMixin(MarketView):
    """Mixin providing Ajax-JSON response functionality."""

    def response(self, context):
        """Return contect as JSON (expects 'status' and 'message' keys there)."""
        if self.request.is_ajax():
            return HttpResponse(json.dumps(context))
        getattr(messages, context['status'])(self.request, context['message'])
        return redirect('admin-home')


class OrderProcessor(MarketView):
    """Mixin to dispatch based on state of order in `request`."""

    input_state = 0
    output_state = 0

    def __init__(self, *args, **kwargs):
        """Set up order to None."""
        self.order = None
        super(OrderProcessor, self).__init__(*args, **kwargs)

    def redirect_based_on_state_of(self, request, order):
        """Do the actual redirect based on order state."""
        if not self.order:
            messages.error(request, _("There is no order for this user"))
            return redirect('home')

        if order.is_processing():
            return redirect(reverse('checkout-shipping'))
        elif order.is_confirming():
            return redirect(reverse('checkout-payment'))
        elif order.is_confirmed():
            return redirect(reverse('order-download', kwargs=dict(
                uid=order.uid, document='proforma')))
        return redirect(reverse('order-download', kwargs=dict(
            uid=order.uid, document='invoice')))

    def dispatch(self, request, *args, **kwargs):
        """Dispatch based on order status."""
        self.order = utils.get_order_from_request(request)

        if self.order.status != self.input_state:
            return self.redirect_based_on_state_of(request, self.order)
        return super(OrderProcessor, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        """Add order to context."""
        ctx = super(OrderProcessor, self).get_context_data(*args, **kwargs)
        if self.order is not None:
            self.order.update_costs()
        ctx.setdefault("order", self.order)
        # Don't update existing suborders bcs they might hold instances of shipping forms
        ctx.setdafault("suborders", self.order.suborders.all())
        return ctx

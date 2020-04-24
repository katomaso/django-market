from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseBadRequest
from django.utils.translation import ugettext as _
from market.core.views import MarketView
from market.core import models as core_models

from market.utils.models import try_get
from market.core.views import VendorRequiredMixin

from market.checkout import models
from marcket.checkout.views import AjaxResponseMixin


class Download(LoginRequiredMixin, View):
    """Force download of invoice/proforma for a vendor."""

    def get(self, request, uid, document):
        """Find proforma/invoice by Order's UID."""
        if document not in ("proforma", "invoice"):
            raise Http404()

        order = get_object_or_404(models.Order, uid=uid)
        order_user = order.order.user if order.is_suborder() else order.user
        vendor_user = order.vendor.user
        if request.user not in (order_user, vendor_user):
            raise Http404()

        if not hasattr(order, document):
            # if the document was not generated - there was a reason for it
            raise Http404()

        if document == "proforma":
            # the user can get proforma any time
            return order.proforma.export_response()

        if document == "invoice" and (order.is_paid() or order.is_shipped()):
            return order.invoice.export_response()

        return HttpResponseBadRequest(_("Invalid request or permissions"))


class OrderDetail(LoginRequiredMixin, MarketView):
    """Show one order specified by UID.

    The actions depend on the requester - if it is a vendor or a customer and they are solved in
    template.
    """

    def get_context_data(self, slug, *args, **kwargs):
        """Add Order from user perspective."""
        ctx = super(OrderDetail, self).get_context_data()
        vendor = try_get(core_models.Vendor, user=self.request.user)
        order = try_get(models.Order, uid=slug, user=self.request.user)
        if not order and vendor:
            order = try_get(models.Order, uid=slug, vendor=vendor)
            ctx.update(vendor=vendor)
        if not order:
            raise Http404(_("No such order"))
        ctx.update(object=order)
        return ctx


class OrderList(VendorRequiredMixin, LoginRequiredMixin, MarketView):
    """models.Order list view for vendors.

    Normal people will have a widget in their admin homepage, since they need to see the last 10.
    """

    states = ('shipped', 'completed', 'confirmed')

    def get(self, request):
        """Add orders with status in `GET['status'] into context."""
        ctx = self.get_context_data()
        status = request.GET.get("status", "shipped")
        if status not in self.states:
            raise Http404('Not a valid status')
        ctx.update(object_list=models.Order.objects.filter(
            vendor=self.vendor, status=getattr(models.Order, status.upper())))
        for s in self.states:
            ctx.update({"%s_count" % s: models.Order.objects.filter(vendor=self.vendor,
                        status=getattr(models.Order, status.upper())).count()})
        ctx.update(status=status)
        return self.render_to_response(ctx)


class ChangeOrderStatus(AjaxResponseMixin, MarketView):
    """(Ajax) view for changing order state.

    - GET should be used for marking orders by its customer
    - POST is exclusively for order's seller
    """

    def get(self, request, uid, status, secret):
        """Change order status by its customer."""
        order = get_object_or_404(models.Order, uid=uid)
        vendor = try_get(core_models.Vendor, user=request.user, active=True)

        try:
            self.change_status(order, int(request.POST['status']), vendor)
        except ValueError as e:
            messages.error(request, str(e))
            return self.render_to_response({"order": order, "error": str(e)})

        messages.success(request, _("models.Order marked as ") + order.get_status_display())
        return self.render_to_response({"order": order})

    def post(self, request, *args, **kwargs):
        """Change the models.Order's status by its seller."""
        if "uid" not in request.POST:
            return HttpResponseBadRequest("Specify an UID")
        order = get_object_or_404(models.Order, uid=request.POST['uid'])
        vendor = try_get(core_models.Vendor, user=request.user, active=True)

        try:
            self.change_status(order, int(request.POST['status']), vendor)
        except ValueError as e:
            return self.response({"status": "error",
                                  "message": str(e)})

        return self.response({"status": "success",
                              "message": order.get_status_display()})

    def change_status(self, order, status, vendor=None):
        """Change order's status from point of its seller."""
        if status <= order.status:
            raise ValueError(_("Cannot lower order's status."))
        if status == models.Order.CANCELLED:
            raise ValueError(_("Seller cannot cancel an order."))
        return order.mark_as(status)


change_order_status = ChangeOrderStatus.as_view()

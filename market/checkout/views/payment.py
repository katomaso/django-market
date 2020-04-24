# coding: utf-8

from allauth import account
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from . import utils


@transaction.atomic
def pay_on_delivery(request):
    """Do not do anything since the order is already confirmed."""
    order = utils.get_order_from_request(request)
    if request.user != order.user:
        messages.error(request, _("You are trying to see order you don't own."))
        return redirect("login")

    conditions = (
        request.user.has_usable_password(),
        account.models.EmailAddress.objects.filter(
            email=request.user.email, primary=True, verified=True).exists(),
    )
    if all(conditions):
        order.mark_as_confirmed()
    else:
        order.mark_as_unconfirmed()
    return redirect("checkout-thanks")


# class mTransferBackend():
#    """
#    Every bank transfer goes over mTransfer so we can operate the money immediately.

#    The backend marks top-level order (or the order itself) as CONFIRMED before
#    further processing. Then a external service is called and if it succeed then
#    the top-level order is marked COMPLETED (by hooks all subsequent orders should
#    be marked the same).
#    """
#    @on_method(vendor_login_required)
#    @on_method(order_required)
#    def entry_view(self, request):
#        """
#        Top-level order does not have any contractor in this case.
#        Don't complete anything - the order was not paid."""
#        order = get_order_from_request(request)
#        return HttpResponseRedirect(self._forge_url(order))

#    @on_method(vendor_login_required)
#    @on_method(order_required)
#    def callback_view(self, request):
#        order = get_order_from_request(request)
#        everything_went_well = True
#        if not everything_went_well:
#            messages.error(request, _("Some problem with mBank payment"))
#            return redirect('checkout-payment')

#        order.mark_as_completed(save=True)
#        return redirect('checkout-thanks')

#    def _forge_url(self, order, **kwargs):
#        return "https://mplatba.mbank.cz/?key=XXXX&amount=10000&callback=" + \
#                reverse('checkout-payment-mtransfer-callback')

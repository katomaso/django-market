# coding: utf-8
import dbmail
import logging

from allauth import account
from allauth.account import signals as account_signals

from django.forms import models as model_forms

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.dispatch import receiver
from django.utils.translation import ugettext as _
from django.shortcuts import redirect

from market.core.views import MarketView, MarketFormView
from market.core import models as core_models
from market.core import forms as core_forms
from market.core import utils as core_utils

from market.checkout import models
from market.checkout import utils
from market.checkout import forms
from market.checkout.views import OrderProcessor

logger = logging.getLogger(__name__)


class Selection(MarketView):
    """Transform cart into an models.Order meanwhile firing `cart_pre_process`."""

    def get_context_data(self, **kwargs):
        """Override the context from the normal template view."""
        ctx = super().get_context_data(**kwargs)
        ctx['cart'] = utils.get_or_create_cart(self.request)

        if self.request.user.is_authenticated():
            ctx['shipping'], ctx['billing'] = self.request.user.shipping_billing()
        else:
            # forms can contain errors so do not replace existing instances
            ctx.setdefault('email_form', core_forms.SecuredEmailForm())

        ctx.setdefault('addresses_form', core_forms.AddressesForm(
            data=None,
            billing=core_utils.get_billing_address_from_request(self.request),
            shipping=core_utils.get_shipping_address_from_request(self.request),
            billing_form_class=self.get_billing_form_class(),
            shipping_form_class=self.get_shipping_form_class(),
        ))

        ctx.setdefault('extra_info_form', model_forms.modelform_factory(
            models.OrderExtraInfo, exclude=['order'])(None))
        return ctx

    def dispatch(self, request, *args, **kwargs):
        """Allow only non-empty carts to go through."""
        cart = utils.get_or_create_cart(self.request)
        if cart.items.count() == 0:
            messages.error(request, _("Cannot checkout empty cart"))
            return redirect("cart")
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Create a user account in case of anonymous user."""
        if "abort" in request.POST:
            # we haven't created order so just quit
            return redirect("cart")

        addresses_form = core_forms.AddressesForm(
            data=request.POST,
            billing=core_utils.get_billing_address_from_request(self.request),
            shipping=core_utils.get_shipping_address_from_request(self.request),
            billing_form_class=self.get_billing_form_class(),
            shipping_form_class=self.get_shipping_form_class(),
        )
        kwargs['addresses_form'] = addresses_form

        if request.user.is_anonymous():
            # create a user account for anonymous and log him in
            adapter = account.adapter.get_adapter(request)
            # first verify email and included captcha form
            email_form = core_forms.SecuredEmailForm(request.POST, request=request)
            kwargs['email_form'] = email_form
            if not (email_form.is_valid() and addresses_form.is_valid()):
                return self.get(request, *args, **kwargs)

            # if EmailForm showed password and it was correct it would return user
            user = email_form.cleaned_data.get("user")
            if user is None:
                email = email_form.cleaned_data['email']
                # if email and captcha is alright then register the user
                # addresses_form.full_clean()
                name = addresses_form.cleaned_data['shipping'].get('name') or \
                       addresses_form.cleaned_data['billing'].get('name')

                user, created = core_models.User.objects.get_or_create(name=name, email=email)
                mail_context = {'user': user}

                if created:
                    email_address = account.models.EmailAddress.objects.add_email(
                        request, user, email, confirm=False, signup=False)
                    email_address.set_as_primary()

                # email saying that we have saved user's login informations
                # with one-time login link 'admin-email-login'
                dbmail.send_db_mail("core-email-login", email, mail_context, user=user)

                # Do not send email confirmation - confirm the email
                # once the order itself is confirmed by email link
                # account.models.EmailConfirmation.create(email_address)

            # login new user without requesting their password
            adapter.login(request, user)

        # assigns Cart to new User in case user accound didn't exist before
        cart = utils.get_or_create_cart(self.request)
        if cart.user != request.user:
            cart.user = request.user
            cart.save()
        # check whether all products in the cart are not sold out.
        remove = []
        for cartitem in cart.items.all():
            if cartitem.item.quantity >= 0 and cartitem.quantity > cartitem.item.quantity:
                remove.append(cartitem)
                messages.warning(
                    request,
                    str(cartitem.item) + " " + str(_("has been sold out.")))
            if not cartitem.item.active:
                remove.append(cartitem)
                messages.warning(
                    request,
                    str(cartitem.item) + " " + str(_("has been removed by vendor.")))
        for cartitem in remove:
            cartitem.delete()

        # save precious adresses into database and request
        extra_info_form = model_forms.modelform_factory(
            models.OrderExtraInfo, exclude=['order'])(request.POST)
        kwargs['extra_info_form'] = extra_info_form

        if not all((addresses_form.is_valid(), extra_info_form.is_valid())):
            return self.get(self, *args, **kwargs)

        # Add the address to the request
        billing_address, shipping_address = \
            addresses_form.save_to_request(self.request)

        # Here it is! Turn Cart into Order!
        order = models.Order.objects.create_from_cart(cart, self.request)
        utils.add_order_to_request(self.request, order)

        # Save addresses into the order
        order.set_shipping_address(shipping_address)
        order.set_billing_address(billing_address)
        order.save()

        return redirect("checkout-shipping")

    def get_shipping_form_class(self):
        """Provided for extensibility."""
        return model_forms.modelform_factory(
            core_models.Address, exclude=['user_shipping', 'user_billing'])

    def get_billing_form_class(self):
        """Provided for extensibility."""
        return model_forms.modelform_factory(
            core_models.Address, exclude=['user_shipping', 'user_billing'])


class Shipping(OrderProcessor, LoginRequiredMixin, MarketView):
    """Select shipping option and mark PROCESSING order as CONFIRMING."""

    input_state = models.Order.PROCESSING

    def get_context_data(self, *args, **kwargs):
        """Add formset of suborders."""
        ctx = super().get_context_data(*args, **kwargs)
        ctx.setdafault("formset", forms.ShippingFormSet(queryset=self.order.suborders))
        return ctx

    def post(self, request, *args, **kwargs):
        """Save different types of shipping into every order.

        Then let a shipping backend to add costs and change states of the orders.
        """
        if "abort" in request.POST:
            return abort_checkout(request)

        formset = forms.ShippingFormSet(
            data=request.POST, queryset=self.order.suborders)
        kwargs['formset'] = formset

        if not formset.is_valid():
            return self.get(request, *args, **kwargs)

        formset.save(commit=True)

        # charge the most expensive item to ship as the seller-shipping orders
        for suborder in self.order.suborders.filter(shipping=True):
            suborder.add_shipping_costs(
                _("Shipping"), suborder.get_potential_shipping())

        # We are done with shippings
        self.order.mark_as_confirming()
        return redirect('checkout-payment')


class Payment(OrderProcessor, LoginRequiredMixin, MarketFormView):
    """Summarize the order and offer link for payment.

    Once user sends this form by clicking on "confirm" button we mark this
    Order as CONFIRMED.

    The optional payment backend will decide if the order should be marked as PAID.
    """

    input_state = (models.Order.CONFIRMING, models.Order.CONFIRMED)
    form_class = forms.PaymentForm

    def form_invalid(self, form):
        """Form can be invalid but just because user wants to abort checkout."""
        if "abort" in self.request.POST:
            return abort_checkout(self.request)
        return super().form_invalid(form)

    def form_valid(self, form):
        """Confirm Order and (optionally) pass it to a payment backend."""
        if "abort" in self.request.POST:
            return abort_checkout(self.request)

        if self.request.user.primary_email.verified:
            self.order.mark_as_confirmed()
        else:
            self.order.mark_as_unconfirmed()

        if form.cleaned_data['payment'] is None:
            return redirect('checkout-thanks')

        return redirect(form.cleaned_data['payment'].url_name)


@receiver(account_signals.email_confirmed)
def handler_email_confirmed(sender, request, email_address, **kwargs):
    """Confirm all unconfirmed orders upon email verification."""
    unconfirmed_orders = models.Order.objects.filter(
        user=email_address.user, status=models.Order.UNCONFIRMED)
    for order in unconfirmed_orders:
        order.mark_as_confirmed()


class ThankYou(MarketView):
    """Thank you view with confirmation of successful placement of an order.

    We will notify the user that if they have unusable password it is necessary
    to confirm their order by clicking on a link in the email.
    """

    def get(self, request, slug=None):
        """Clean cart and handle order confirmation via email.

        Param `key` is in fact UID of an (un)confirmed order.
        """
        utils.get_cart_from_request(self.request).empty()
        return super().get(self, request)

    def get_context_data(self, **kwargs):
        """Add order instance to context.

        We can't use `OrderProcessor` because it is looking only on < CONFIRMED
        orders and that is correct.
        """
        context = super(ThankYou, self).get_context_data(**kwargs)
        context["order"] = (models.Order.objects
                            .filter(order__isnull=True,
                                    status__in=(models.Order.CONFIRMED,
                                                models.Order.UNCONFIRMED,
                                                models.Order.PAID))
                            .latest('created'))
        if not self.request.user.has_usable_password():
            context.setdefault("password_form",
                               account.forms.SetPasswordForm(self.request.user))
        return context

thank_you = ThankYou.as_view()


def abort_checkout(request):
    """Cancel order in `request and redirect to cart."""
    order = utils.get_order_from_request(request)
    order.mark_as_canceled()
    messages.info(request, _("Your order was canceled"))
    # instead of deleting the cart as well - let the user to do it
    return redirect('cart')

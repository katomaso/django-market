# coding: utf-8
from django.utils.translation import gettext as _
from market.core.urls import api
from urljects import U, slug, url

from market.checkout.views import cart, checkout, order, payment

action = slug.replace("slug", "action")

def active(user):
    """Check if the user is active with verified email."""
    from allauth.account.models import EmailAddress
    return (
        user.is_authenticated() and
        not EmailAddress.objects.filter(user=user, verified=False).exists()
    )

urlpatterns = [
    # cart views to allow user to gather their goods into a shopping cart
    api(U / _('cart/'), cart.Cart, name='cart'),
    api(U / _('cart/') / _('item'), cart.CartItem, name='cart-item'),

    # checkout to facilitate pro porcess of payments and selecting shipping
    # first part with address form and shipping/payment selection
    url(U / _('select.html'), checkout.Selection, name="checkout-selection"),
    # second step of the checkout process
    url(U / _('shipping.html'), checkout.Shipping, name='checkout-shipping'),
    # third step of the checkout process
    url(U / _('payment.html'), checkout.Payment, name='checkout-payment'),
    # canceling of current order
    url(U / _('cancel.html'), checkout.abort_checkout, name='checkout-cancel'),
    # confirm email and unconfirmed orders
    url(U / _('thank-you/') / (slug + '.html'), checkout.thank_you, name='checkout-thanks'),
    # if any
    url(U / _('thank-you.html'), checkout.thank_you, name='checkout-thanks'),

    # order views gives user ad vendor to see orders
    url(U / _('order.html'), order.OrderList, name="order-list"),
    url(U / _('order/') / (slug + '.html'), order.OrderDetail, name="order-detail"),
    url(U / _('order/') / _('change-status.json'), order.change_order_status, name='order-change-status'),

    # TODO: checkout-order-shipped order=order.uid
    url(U / _('download/') / slug / '(?P<document>invoice|proforma)', order.Download, name="order-download"),

    # payment backends (other can be in separate apps)
    url(U / _('payment/') / _('cash.html'), payment.pay_on_delivery, name='checkout-pay-on-delivery'),
]

# coding:utf-8
import dbmail
import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction, models
from django.db.models import Sum, Max
from django.dispatch import receiver
from django.utils.translation import ugettext as _

from invoice.models import Invoice

from market.utils import models as utils

from django.utils.functional import cached_property
from market.utils.models import UidMixin
from market.checkout import signals
from market.checkout import managers

from . import serializers

# choose optimized JSONField for default database
if "postgres" in settings.DATABASES['default']['ENGINE']:
    from django.contrib.postgres.fields import jsonb as jsonfield
else:
    import jsonfield



logger = logging.getLogger(__name__)


class PaymentBackend(models.Model):
    """Payment option proposed to a customer.

    Every payment backend has to have an entry in the DB as a PaymentBackend
    model. It will be always referred by its `url_name` therefor the form of URL
    is optional but the registration of the URL is up to the backend itself.
    Usually the payment backend contains either from one (redirect) view which
    signes all orders as CONFIRMED/COMPLETED or two views when the first one
    calls external API and the second one receives callback from the API.
    """

    name = models.CharField(max_length=50)
    url_name = models.SlugField()
    active = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)
    logo = models.ImageField(null=True, blank=True, upload_to=utils.upload_to_classname)

    # payment backend might require token thus we make linking tables
    vendor = models.ManyToManyField('market.Vendor', through='market.VendorPayment')

    class Meta:
        """Explicitely mark the app_label and concrete model."""
        app_label = "market"
        verbose_name = _('Payment backend')
        verbose_name_plural = _('Payment backends')

    def __str__(self):
        return self.name


class VendorPayment(models.Model):
    """Every vendor can have different payment available."""

    vendor = models.ForeignKey('market.Vendor', related_name='payment_backend')
    payment = models.ForeignKey('market.PaymentBackend')
    data = jsonfield.JSONField(help_text=_("Auth information for the payment service"))

    class Meta(object):
        """State explicitely app_label."""
        app_label = "market"
        verbose_name = _('Vendor Payment')

    def __str__(self):
        return " ".join(self.payment.name, _("for"), self.vendor.name)


class OrderExtraInfo(models.Model):
    """A holder for extra textual information to attach to this order."""
    order = models.ForeignKey('market.Order', swappable=True,
                              related_name="extra_info", verbose_name=_('Order'))
    text = models.TextField(verbose_name=_('Extra info'), blank=True)

    class Meta(object):
        """Explicitely mark the app_label and concrete model."""
        app_label = "market"
        verbose_name = _('Order extra info')
        verbose_name_plural = _('Order extra info')


class ExtraOrderPriceField(models.Model):
    """Persistent Cart-provided extra price fields as a "snapshot" at the time of order creation."""
    order = models.ForeignKey('market.Order', related_name='extraitems', verbose_name=_('Order'))
    label = models.CharField(max_length=255, verbose_name=_('Label'))
    value = utils.CurrencyField(verbose_name=_('Amount'))
    data = jsonfield.JSONField(null=True, blank=True, verbose_name=_('Serialized extra data'))
    # Does this represent shipping costs?
    is_shipping = models.BooleanField(default=False, editable=False,
                                      verbose_name=_('Is shipping'))

    class Meta(object):
        """Explicitely mark the app_label."""
        app_label = "market"
        verbose_name = _('Extra order price field')
        verbose_name_plural = _('Extra order price fields')


class ExtraOrderItemPriceField(models.Model):
    """Persistent Cart-provided extra price fields.

    We want to "snapshot" their statuses at the time when the order was made.
    """
    order_item = models.ForeignKey('market.OrderItem', related_name='extraitems',
                                   verbose_name=_('Order item'))
    label = models.CharField(max_length=255, verbose_name=_('Label'))
    value = utils.CurrencyField(verbose_name=_('Amount'))
    data = jsonfield.JSONField(null=True, blank=True, verbose_name=_('Serialized extra data'))

    class Meta(object):
        """Explicitely mark the app_label."""
        app_label = "market"
        verbose_name = _('Extra order item price field')
        verbose_name_plural = _('Extra order item price fields')


class OrderPayment(models.Model):
    """A class to hold basic payment information.

    Backends should define their own more complex payment types should they
    need to store more information.
    """
    order = models.ForeignKey('market.Order', verbose_name=_('Order'))
    # How much was paid with this particular transfer
    amount = utils.CurrencyField(verbose_name=_('Amount'))
    transaction_id = models.CharField(
        max_length=255,
        verbose_name=_('Transaction ID'),
        help_text=_("The transaction processor's reference"))
    payment_method = models.CharField(
        max_length=255,
        verbose_name=_('Payment method'),
        help_text=_("The payment backend used to process the purchase"))

    class Meta(object):
        """Explicitely mark the app_label and concrete model."""
        app_label = "market"
        verbose_name = _('Order payment')
        verbose_name_plural = _('Order payments')


class Cart(models.Model):
    """Vendorping `Cart` handling `Offer`s from multiple vendors."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, swappable=True,
                                null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    serializer = serializers.CartSerializer()

    class Meta:
        """Explicitely mark the app_label."""
        app_label = 'market'
        verbose_name = _('Cart')
        verbose_name_plural = _('Carts')

    def __init__(self, *args, **kwargs):
        """Zero-initialize runtime variables."""
        super().__init__(*args, **kwargs)
        self.subtotal = Decimal('0.0')
        self.total = Decimal('0.0')
        self.extra_price_fields = []  # List of tuples (label, value)
        self.updated_items = None  # cache of updated CartItems (update operates only in memory)
        self.current_total = Decimal('0.0')  # cache of total for cart_modifiers

    def add_modifier(self, label, value):
        """Add rebates/penales to the cart when it is being rendered/ordered."""
        if not isinstance(value, Decimal):
            value = Decimal(value)
        self.extra_price_fields.append((label, value))
        self.current_total += value

    def add_item(self, item, quantity=1, merge=True, queryset=None):
        """Add a (new) item to the cart.

        The parameter `merge` controls whether we should merge the added
        CartItem with another already existing sharing the same
        product_id. This is useful when you have products with variations
        (for example), and you don't want to have your products merge (to loose
        their specific variations, for example).

        A drawback is that generally  setting `merge` to ``False`` for
        products with variations can be a problem if users can buy thousands of
        products at a time (that would mean we would create thousands of
        CartItems as well which all have the same variation).

        The parameter `queryset` can be used to override the standard queryset
        that is being used to find the CartItem that should be merged into.
        If you use variations, just finding the first CartItem that
        belongs to this cart and the given item is not sufficient. You will
        want to find the CartItem that already has the same variations that the
        user chose for this request.

        Example with merge = True:
        >>> self.items[0] = CartItem.objects.create(..., item=MyProduct())
        >>> self.add_product(MyProduct())
        >>> self.items[0].quantity
        2

        Example with merge = False:
        >>> self.items[0] = CartItem.objects.create(..., item=MyProduct())
        >>> self.add_product(MyProduct())
        >>> self.items[0].quantity
        1
        >>> self.items[1].quantity
        1
        """
        # check if item can be added at all
        assert item.active, "Cannot add inactive item"

        # get the last updated timestamp
        # also saves cart object if it is not saved
        self.save()

        queryset = queryset or CartItem.objects.filter(cart=self, item=item)

        # Let's see if we already have an Item with the same item ID
        if queryset.exists() and merge:
            cart_item = queryset.get()
            return self.update_quantity(cart_item.id, cart_item.quantity + int(quantity))

        cart_item = CartItem.objects.create(cart=self, quantity=quantity, item=item)
        return cart_item

    def update_quantity(self, cart_item_id, quantity):
        """Update quantity for `cart_item_id` or delete if `quantity` is 0."""
        if quantity == 0:
            return self.delete_item(cart_item_id)
        cart_item = self.items.get(pk=cart_item_id)
        cart_item.quantity = quantity
        cart_item.save()
        self.save()
        return cart_item

    def delete_item(self, cart_item_id):
        """A simple convenience method to delete one of the cart's items.

        This allows to implicitely check for "access rights" since we insure the
        cartitem is actually in the user's cart.
        """
        cart_item = self.items.get(pk=cart_item_id)
        cart_item.delete()
        self.save()

    def get_updated_cart_items(self):
        """Return items after update() has been called and thus modifiers executed."""
        assert self.updated_items is not None, (
            'Cart needs to be updated before calling get_updated_cart_items.')
        return self.updated_items

    def update(self, request=None):
        """To be called whenever any item is added/removed in the cart.

        It will loop on all line items in the cart, and call all the price
        modifiers on each row.
        After doing this, it will compute and update the order's total and
        subtotal fields, along with any payment field added along the way by
        modifiers.

        Note that theses added fields are not stored - we actually want to
        reflect rebate and tax changes on the *cart* items, but we don't want
        that for the order items (since they are legally binding after the
        "purchase" button was pressed)
        """
        self.extra_price_fields = []  # Reset the price fields
        self.subtotal = Decimal('0.0')  # Reset subtotal
        self.total = Decimal('0.0')  # Reset total

        # This calls all the cart_pre_process methods (if any), before the cart
        # is processed. This allows for data collection on the cart for
        # example)
        signals.cart_pre_process.send(
            sender=self.__class__, cart=self, request=request)

        self.updated_items = self.items.all()
        for item in self.updated_items:
            item.update(request)
        self.total += sum(item.total for item in self.updated_items)

        self.current_total = self.total
        signals.cart_post_process.send(
            sender=self.__class__, cart=self, request=request)

        # in case modifiers got too wild and put negative price - round it back
        if self.current_total < 0:
            self.add_modifier(_("Automatic rounding to 0"), abs(self.current_total))

        self.total = self.current_total
        return self.total

    def empty(self):
        """Remove all cart items."""
        if self.pk:
            self.items.all().delete()
            self.delete()

    @property
    def total_quantity(self):
        """Total quantity of all items in the cart."""
        return sum(ci.quantity for ci in self.items.all())

    @property
    def is_empty(self):
        """Current cart has no items."""
        return self.total_quantity == 0

    def __str__(self):
        return _("Cart for") + " " + str(self.user)

    @property
    def vendors(self):
        """List of vendors participating on this cart."""
        return self.items.distinct("product__vendor").values_list("product__vendor", flat=True)

    def items_by_vendor(self):
        """Group items together by vendor.

        :returns: list of dicts{"vendor": <vendor-instance>, "items": [<item-instance>...]}
        """
        result = []
        cache = {}
        vendor = None
        for item in self.items.all().order_by("product__vendor"):
            if item.product.vendor != vendor:
                if cache:
                    result.append(cache)
                cache = {'vendor': item.product.vendor, 'items': []}
                vendor = item.product.vendor
            cache['items'].append(item)
        if cache:
            result.append(cache)
        return result


class CartItem(models.Model):
    """Holder for the quantity and pointer to actual `Product`s."""

    cart = models.ForeignKey('market.Cart', related_name="items")
    quantity = models.IntegerField()
    item = models.ForeignKey('market.Offer')
    serializer = serializers.CartItemSerializer()

    class Meta:
        """Explicitely mark the app_label and concrete model."""
        app_label = "market"
        verbose_name = _('Cart item')
        verbose_name_plural = _('Cart items')

    def __init__(self, *args, **kwargs):
        """Hold extra fields to display to the user (ex. taxes, discount)."""
        super().__init__(*args, **kwargs)
        self.extra_price_fields = []  # list of tuples (label, value)
        # These must not be stored, since their components can be changed
        # between sessions / logins etc...
        self.subtotal = Decimal('0.0')
        self.total = Decimal('0.0')
        self.current_total = Decimal('0.0')  # Used by cart modifiers

    def add_modifier(self, label, value):
        """Add rebates/penales to the cart item when cart is being rendered/ordered."""
        if not isinstance(value, Decimal):
            value = Decimal(value)
        self.extra_price_fields.append((label, value))
        self.current_total += value

    def update(self, request):
        """Give apps the chance to modify single cart items."""
        self.extra_price_fields = []  # Reset the price fields
        self.subtotal = self.item.unit_price * self.quantity
        self.total = self.item.price * self.quantity

        # backup ``total`` into ``current_total`` because receivers will modify it
        self.current_total = self.total
        # We now loop over every registered price modifier,
        # most of them will simply add a field to extra_payment_fields
        signals.cart_item_process.send_robust(
            sender=self.__class__, cart_item=self, request=request)

        if self.current_total < 0:
            self.add_modifier(_("Automatic rounding to 0"), abs(self.current_total))

        self.total = self.current_total
        return self.total


class OrderItem(models.Model):
    """A line Item for an order."""

    order = models.ForeignKey('market.Order', swappable=True,  # get_model_string('Order')
                              related_name='orderitems', verbose_name=_('Order'))
    item_reference = models.CharField(max_length=255,
                                      verbose_name=_('Item reference'))
    item_name = models.CharField(max_length=255, null=True, blank=True,
                                 verbose_name=_('Item name'))
    item = models.ForeignKey('market.Offer',
                             null=True, verbose_name=_('Item'), blank=True)
    unit_price = utils.CurrencyField(verbose_name=_('Unit price'))
    quantity = models.IntegerField(verbose_name=_('Quantity'))
    subtotal = utils.CurrencyField(verbose_name=_('Line subtotal'))
    total = utils.CurrencyField(verbose_name=_('Line total'))

    class Meta(object):
        """Explicitely mark the app_label and concrete model."""
        app_label = 'market'
        verbose_name = _('Order item')
        verbose_name_plural = _('Order items')

    def save(self, *args, **kwargs):
        """Copy the name from referenced item."""
        if not self.item_name and self.item:
            self.item_name = self.item.get_name()


class Order(UidMixin, models.Model):
    """A model representing an Order top-order <-> suborder relation.

    An order is the "in process" counterpart of the vendorping cart, which holds
    stuff like the shipping and billing addresses (copied from the User
    profile) when the Order is first created), list of items, and holds stuff
    like the status, shipping costs, taxes, etc.
    """

    PROCESSING = 10  # New order, addresses and shipping/payment being chosen
    CONFIRMING = 20  # The order is pending confirmation (user is at the confirm view)
    UNCONFIRMED = 25  # Order was confirmed by an anonymous user
    CONFIRMED = 30  # The order was confirmed (user is in the payment backend)
    COMPLETED = 40  # Payment backend successfully completed
    PAID = COMPLETED  # Payment backend successfully completed
    SHIPPED = 45  # The order was shipped to client
    RECEIVED = 50  # The order was received by the client
    DONE = RECEIVED
    CANCELED = 60  # The order was canceled

    STATUSES = (
        PROCESSING,
        CONFIRMING,
        UNCONFIRMED,
        CONFIRMED,
        PAID,
        SHIPPED,
        RECEIVED,
        CANCELED
    )

    STATUS_CODES = (
        (PROCESSING, _('Processing')),
        (CONFIRMING, _('Confirming')),
        (UNCONFIRMED, _('Unconfirmed')),
        (CONFIRMED, _('Confirmed')),
        (PAID, _('Paid')),
        (SHIPPED, _('Shipped')),
        (RECEIVED, _('Received')),
        (CANCELED, _('Canceled')),
    )

    STATUS_TO_SIGNALS = {
        UNCONFIRMED: signals.order_unconfirmed,
        CONFIRMED: signals.order_confirmed,
        PAID: signals.order_paid,
        SHIPPED: signals.order_shipped,
        RECEIVED: signals.order_received,
        CANCELED: signals.order_cancelled,
    }

    order = models.ForeignKey('self', on_delete=models.CASCADE, related_name="suborders", null=True)
    vendor = models.ForeignKey('market.Vendor', on_delete=models.CASCADE, related_name="orders", null=True)
    cart = models.ForeignKey('market.Cart', blank=True, null=True, on_delete=models.SET_NULL)
    # might be filled in the process
    user = models.ForeignKey(settings.AUTH_USER_MODEL, swappable=True,
                             blank=True, null=True, verbose_name=_('User'))
    status = models.IntegerField(choices=STATUS_CODES, default=PROCESSING, verbose_name=_('Status'))
    subtotal = utils.CurrencyField(verbose_name=_('Order subtotal'))
    total = utils.CurrencyField(verbose_name=_('Order Total'))

    shipping_address_text = models.TextField(_('Shipping address'), blank=True, null=True)
    shipping = models.BooleanField(default=False, blank=True,
                                   help_text=_("Marks if seller ships the order"))
    billing_address_text = models.TextField(_('Billing address'), blank=True, null=True)
    payment_backend = models.ForeignKey('market.PaymentBackend', blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))
    modified = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    proforma = models.OneToOneField('invoice.Invoice', null=True, related_name="+")
    invoice = models.OneToOneField('invoice.Invoice', null=True, related_name="+")
    message = models.TextField(null=True, blank=True)

    objects = managers.OrderManager()

    class Meta(object):
        """Explicitely mark the app_label and concrete model."""
        app_label = 'market'
        ordering = ['status', 'created']
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')

    def __str__(self):
        user = self.get_user()
        if user:
            return u"{0} #{1} {2} {3} - {4}".format(
                _("Order"), self.pk, _("from"), user.name, self.total)
        return u"{0} #{1} - {2}".format(_("Order"), self.pk, self.total)

    def is_fully_paid(self):
        """Check if this order was really fully paid."""
        return self.amount_paid >= self.total

    def is_processing(self):
        return self.status == self.PROCESSING

    def is_completed(self):
        return self.status == self.PAID

    def is_paid(self):
        return self.status == self.PAID

    def is_shipped(self):
        return self.status == self.SHIPPED

    def is_unconfirmed(self):
        return self.status == self.UNCONFIRMED

    def is_confirmed(self):
        return self.status == self.CONFIRMED

    def is_confirming(self):
        return self.status == self.CONFIRMING

    def is_received(self):
        return self.status == self.RECEIVED
    is_done = is_received

    def get_status_name(self):
        return dict(self.STATUS_CODES)[self.status]

    def mark_as(self, status, save=True):
        """The only way of changing the state of the order and it's suborders."""
        if status not in self.STATUSES:
            raise KeyError("Status not listed in Order.STATUS_CODES")
        self.status = status
        if save:
            self.save()
        if status in self.STATUS_TO_SIGNALS.keys():
            self.STATUS_TO_SIGNALS[status].send(self.__class__, order=self)
        if self.is_suborder():
            return self
        lowstatus_suborders = self.suborders.filter(status__lt=status)
        if lowstatus_suborders.exists():
            for suborder in lowstatus_suborders:
                suborder.mark_as(status, save)
        return self

    def mark_as_confirming(self, save=True):
        self.mark_as(self.CONFIRMING, save)

    def mark_as_unconfirmed(self, save=True):
        self.mark_as(self.UNCONFIRMED, save)

    def mark_as_confirmed(self, save=True):
        self.mark_as(self.CONFIRMED, save)

    def mark_as_completed(self, save=True):
        self.mark_as(self.PAID, save)

    def mark_as_paid(self, save=True):
        self.mark_as(self.PAID, save)

    def mark_as_shipped(self, save=True):
        self.mark_as(self.SHIPPED, save)

    def mark_as_received(self, save=True):
        self.mark_as(self.RECEIVED, save)
    mark_as_done = mark_as_received

    def mark_as_canceled(self, save=True):
        self.mark_as(self.CANCELED, save)

    @property
    def amount_paid(self):
        """The amount paid is the sum of related orderpayments."""
        q = OrderPayment.objects.all()
        q = q.filter(order=self) if self.is_suborder else q.filter(order__in=self.suborders.all())
        return q.aggregate(sum=Sum('amount')).get('sum') or Decimal('0.00')

    def add_shipping_costs(self, name, amount):
        """Create ExtraOrderPriceField with shipping costs for this order."""
        from vendor.models import ExtraOrderPriceField
        if isinstance(amount, float):
            value = Decimal("%.2f".format(amount))
        else:
            value = amount
        return ExtraOrderPriceField.objects.get_or_create(
            order=self,
            label=name,
            is_shipping=True,
            value=value
        )[0]

    @property
    def shipping_costs(self):
        """Compute shipping costs of the whole order (readonly)."""
        q = ExtraOrderPriceField.objects.filter(is_shipping=True)
        q = q.filter(order=self) if self.is_suborder() else q.filter(order__in=self.suborders.all())
        return q.aggregate(sum=Sum('value')).get('sum') or Decimal(0)

    def update_costs(self):
        """Update all costs in case shipping or other things has changed."""
        if not self.is_suborder():
            self.subtotal = Decimal('0.00')
            self.total = Decimal('0.00')
            for suborder in self.suborders.all():
                suborder.update_costs()
                self.subtotal += suborder.subtotal
                self.total += suborder.total
            self.save()
            return

        prev_subtotal = self.subtotal or Decimal('0.00')
        self.subtotal = (
            self.orderitems.all().aggregate(subtotal=Sum("subtotal"))["subtotal"]
        ) or Decimal('0.00')

        prev_total = self.total or Decimal('0.00')
        self.total = (
            self.orderitems.all().aggregate(total=Sum("total"))["total"] or Decimal('0.00') +
            self.shipping_costs
        )

        if prev_subtotal != self.subtotal or prev_total != self.total:
            self.save()

    @property
    def short_name(self):
        """A short name to be displayed on the payment processor's website."""
        return "%s-%s" % (self.pk, self.total)

    def set_billing_address(self, billing_address):
        """Save a copy of billing address at the moment.

        You can override this method to process address more granulary
        e.g. you can copy address instance and save FK to it in your order
        class.
        """
        if hasattr(billing_address, 'as_text') and callable(billing_address.as_text):
            self.billing_address_text = billing_address.as_text()
            self.save()
    billing_address = property(lambda self: self.billing_address_text,
                               set_billing_address)

    def set_shipping_address(self, shipping_address):
        """Save a copy of shipping address at the moment.

        You can override this method to process address more granulary
        e.g. you can copy address instance and save FK to it in your order
        class.
        """
        if hasattr(shipping_address, 'as_text') and callable(shipping_address.as_text):
            self.shipping_address_text = shipping_address.as_text()
            self.save()
    shipping_address = property(lambda self: self.shipping_address_text,
                                set_shipping_address)

    def is_suborder(self):
        """Reveal if the current order is a suborder."""
        return self.order is not None

    def get_user(self):
        """Get the user for this order."""
        if self.user:
            return self.user
        if self.order:
            return self.order.user
        return None

    def pay_on_delivery(self):
        """Check if the payment is on-delivery."""
        return (self.payment_backend is None or
                self.payment_backend.url_name == "checkout-pay-on-delivery")

    def get_potential_shipping(self):
        """Estimate shipping costs."""
        return (self.orderitems.aggregate(max=Max("item__shipping_price"))
                               .get("max", Decimal(0)))

    @cached_property
    def payment(self):
        """Such as `shipping` is per-order this is a hack to make payment per order."""
        if self.is_suborder():
            return self.order.payment_backend
        return self.payment_backend

    @property
    def item_set(self):
        """Gather all related OrderItems from potentially all suborders."""
        from vendor.models import OrderItem
        if self.order:
            return self.orderitems.all()
        return OrderItem.objects.filter(order__in=self.suborders.all())

    @property
    def extraitem_set(self):
        """The original name is just too fuckin long."""
        if self.order:
            return self.extraitems.all()
        return ExtraOrderPriceField.objects.filter(order__in=self.suborders.all())

    def _create_invoice_draft(self, contractor, subscriber):
        logo = contractor.logo.path if contractor.logo else None

        invoice = Invoice.objects.create(
            contractor=contractor.address, subscriber=subscriber.billing,
            contractor_bank=contractor.bank_account, logo=logo)

        for orderitem in self.item_set:
            invoice.add_item(orderitem.item_name, orderitem.unit_price,
                             orderitem.item.tax, orderitem.quantity)
        for extraitem in self.extraitem_set:
            invoice.add_item(extraitem.label, extraitem.value, tax=0, quantity=1)
        return invoice

    @transaction.atomic
    def create_legal_documents(self):
        """Invoice and proforma has to exist for any suborder."""
        if self.is_suborder() and self.proforma is None:
            self.proforma = self._create_invoice_draft(
                contractor=self.vendor,
                subscriber=self.order.user)
            self.proforma.state = Invoice.STATE_PROFORMA
            self.proforma.save()

        if self.is_suborder() and self.invoice is None:
            self.invoice = self._create_invoice_draft(
                contractor=self.vendor,
                subscriber=self.order.user)
            self.invoice.state = Invoice.STATE_INVOICE
            self.invoice.save()
            self.save()


@receiver(signals.order_shipped)
def order_shipped_mailer(sender, order, **kwargs):
    """Email customer about shipped order."""
    if not order.is_suborder():
        return
    customer = order.order.user
    seller = order.vendor.user
    context = {"order": order,
               "vendor": order.vendor,
               "customer": customer,
               "seller": seller}
    dbmail.send_db_mail('checkout-shipped-customer', customer.email, context,
                        reply_to=[seller.email, ])


@receiver([signals.order_completed, signals.order_shipped, signals.order_confirmed])
def order_state_coherency(sender, order, **kwargs):
    """Catch the situation when last suborder changes its state.

    In that case we want to align top-order's state with its suborders.
    """
    if not order.is_suborder():
        return

    top = order.order
    if order.status > top.status:
        # if this suborder has higher state than its toporder
        if not top.suborders.filter(status__lt=top.status).exists():
            # and no other sub-order has lower state than top-order
            top.mark_as(order.status)


@receiver([signals.order_completed, signals.order_shipped])
def order_completed_manual_payment(sender, order, **kwargs):
    """Create an OrderPayment for orders signed as 'paid' but paid in cash / bank transfer.

    The intention is when a seller manually clicks on "completed" then we want to assign a
    payment to the order.
    """
    if not order.is_suborder():
        return

    if order.is_fully_paid():
        return

    if order.pay_on_delivery():
        OrderPayment.objects.create(
            order=order, amount=order.order_total,
            payment_method=order.payment.url_name,
            transaction_id='0'
        )


@receiver([signals.order_unconfirmed, signals.order_confirmed, signals.order_completed])
def order_completed_mailer(sender, order, **kwargs):
    """
    Complete means a payment for the order has arrived.

    This hook sends emails to users about a payment with an according invoice.
    The invoice is ALWAYS created as an user-vendor relation (thus only in suborders)
    """
    if not order.is_suborder():
        return

    order.create_legal_documents()

    seller = order.vendor
    customer = order.order.user

    context = {"order": order,
               "seller": seller.user,
               "customer": customer,
               "vendor": seller}

    if kwargs['signal'] == signals.order_unconfirmed:
        # send confirmation link for their order
        dbmail.send_db_mail('checkout-unconfirmed-customer',
                            customer.email, context)

    if kwargs['signal'] == signals.order_confirmed and order.pay_on_delivery():
        # send a proforma to the user
        dbmail.send_db_mail('checkout-confirmed-customer', customer.email, context,
                            reply_to=[seller.user.email, ],
                            attachments=[order.proforma.export_attachment(), ])
        # send an invoice to the seller
        dbmail.send_db_mail('checkout-confirmed-vendor', seller.user.email, context,
                            reply_to=[customer.email, ],
                            attachments=[order.invoice.export_attachment(), ])

    if kwargs['signal'] == signals.order_completed:
        # send a proforma to the user
        dbmail.send_db_mail('checkout-completed-customer', customer.email, context,
                            reply_to=[seller.user.email, ],
                            attachments=[order.invoice.export_attachment(), ])
        # send an invoice to the seller so they are ready if/when customer steps in
        dbmail.send_db_mail('checkout-completed-vendor', seller.user.email, context,
                            reply_to=[customer.email, ],
                            attachments=[order.invoice.export_attachment(), ])


@receiver(signals.order_completed)
def order_completed_offer_update(sender, order, **kwargs):
    """Completed means a payment for the order has arrived."""
    for item in order.item_set:
        if item.product.quantity > 0:
            item.product.quantity -= item.quantity
            if item.product.quantity < 0:
                item.product.quantity = 0
            item.product.save()


@receiver(signals.order_confirmed)
def order_completed_statistics(sender, order, **kwargs):
    """Update products statistics after order was placed on them."""
    for item in order.item_set:
        offer = item.product
        product = offer.product
        offer.sold += item.quantity
        offer.save()
        product.sold += item.quantity
        product.save()

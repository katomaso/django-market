from decimal import Decimal
from django.db import transaction
from django.db import models

from . import signals


class OrderManager(models.Manager):
    """Handle suborders functionality."""

    def get_latest_for_user(self, user):
        """Return the last order (from a time perspective) of the `user`."""
        if user and not user.is_anonymous():
            return self.filter(user=user, order__isnull=True)\
                       .order_by('-modified')[0]
        else:
            return None

    @transaction.atomic
    def create_from_cart(self, cart, request, status=None):
        """Create suborders to the top-order.

        If the creation of suborders fails, delete the original order.
        """
        """Create atomically a new Order form Cart.

        Specifically, it creates an Order with corresponding OrderItems and
        eventually corresponding ExtraPriceFields

        This will only actually commit the transaction once the function exits
        to minimize useless database access.

        The `request` parameter is further passed to cart_item_process,
        cart_pre_process, and cart_post_process, so it can be used as a way to
        store per-request arbitrary information.

        Emits the ``processing`` signal.
        """
        from . import models

        def apply(func, seq, *args):
            for data in seq:
                func(*(args + data))

        def serialize_order_extra(order, label, price, *data):
            """Serialize cart's extra price fields into database together with Order."""
            models.ExtraOrderPriceField(
                order=order,
                label=str(label),
                value=price if isinstance(price, Decimal) else Decimal(price),
                data=None if not data else data[0]
            ).save()

        def serialize_order_item_extras(order_item, label, price, *data):
            """Serialize cart_item's extra price fields into database together with OrderItem."""
            models.ExtraOrderItemPriceField(
                order_item=order_item,
                label=str(label),
                value=price if isinstance(price, Decimal) else Decimal(price),
                data=None if not data else data[0]
            ).save()

        # trigger all signals and updates
        cart.update(request)

        # First, let's remove old orders
        self.unconfirmed_for_cart(cart).delete()

        # Create an empty order object
        order = self.model(
            user=cart.user,
            vendor=None,
            cart=cart,
            status=status or self.model.PROCESSING,
            subtotal=cart.subtotal,
            total=cart.total,
        )
        suborders = {}
        order.save()
        apply(serialize_order_extra, cart.extra_price_fields, order)

        for cart_item in cart.updated_items:
            suborder = suborders.setdefault(
                cart_item.item.vendor.id,
                self.create(
                    user=None,
                    vendor=cart_item.item.vendor,
                    order=order,
                    status=order.status))
            order_item = models.OrderItem(
                order=suborder,
                item_reference=cart_item.item.slug,
                item_name=cart_item.item.name,
                item=cart_item.item,
                unit_price=cart_item.item.unit_price,
                quantity=cart_item.quantity,
                total=cart_item.total,
                subtotal=cart_item.subtotal)
            order_item.save()
            # For each order item, we save the extra_price_fields to DB
            apply(serialize_order_item_extras, cart_item.extra_price_fields, order_item)

        # update orders prices
        order.update_costs()
        signals.order_processing.send(self.model, order=order, cart=cart)
        return order

    def unconfirmed_for_cart(self, cart):
        """Get all unconfirmed orders for current cart."""
        return self.filter(cart=cart, status__lt=self.model.CONFIRMED)

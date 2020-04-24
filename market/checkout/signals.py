from django import dispatch

"""The best occasion to modify (remove) items in Cart (e.g. based on product availability).

Please make sure to include message what and why happened. That's why we have `request`.
"""
cart_pre_process = dispatch.Signal(providing_args=['cart', 'request'])

"""Emitted when totals of all items available thus is ideal for discounts."""
cart_post_process = dispatch.Signal(providing_args=['cart', 'request'])

"""Emmited per cart_item when subtotal and total=subtotal+tax are available."""
cart_item_process = dispatch.Signal(providing_args=['cart_item', 'request'])


"""Emitted when the Cart was converted to an Order."""
order_processing = dispatch.Signal(providing_args=['order', 'cart'])

"""Emitted when the user is shown the "select a payment method" page."""
order_payment_selection = dispatch.Signal(providing_args=['order'])

"""Emitted when an anonymous user finished placing his order."""
order_unconfirmed = dispatch.Signal(providing_args=['order'])

"""Emitted when an authenticated user finished placing his order regardless
of the payment success or failure."""
order_confirmed = dispatch.Signal(providing_args=['order'])

"""Emitted when the payment was received for the Order."""
order_completed = dispatch.Signal(providing_args=['order'])
order_paid = order_completed

"""Emitted when the Order was received by the customer"""
order_received = dispatch.Signal(providing_args=['order'])
order_done = order_received

"""Emitted (manually) when the vendor clerk or robot shipped the order."""
order_shipped = dispatch.Signal(providing_args=['order'])

"""Emitted if the payment was refused or other fatal problem."""
order_cancelled = dispatch.Signal(providing_args=['order'])

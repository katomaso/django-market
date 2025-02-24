# coding: utf-8
from . import models


def get_cart_from_database(request):
    """Return cart instance for current user from DB storage."""
    database_cart = models.Cart.objects.filter(user=request.user)
    if database_cart:
        database_cart = database_cart[0]
    else:
        database_cart = None
    return database_cart


def get_cart_from_session(request):
    """Return cart instance for current user from session storage."""
    session_cart = None
    session = getattr(request, 'session', None)
    if session is not None:
        cart_id = session.get('cart_id')
        if cart_id:
            try:
                session_cart = models.Cart.objects.get(pk=cart_id)
            except models.Cart.DoesNotExist:
                session_cart = None
    return session_cart


def get_or_create_cart(request, save=False):
    """Get cart for current visitor.

    For a logged in user, try to get the cart from the database. If it's not there or it's empty,
    use the cart from the session.
    If the user is not logged in use the cart from the session.
    If there is no cart object in the database or session, create one.

    If ``save`` is True, cart object will be explicitly saved.
    """
    cart = None
    if not hasattr(request, '_cart'):
        is_logged_in = request.user and not request.user.is_anonymous()

        if is_logged_in:
            # if we are authenticated
            session_cart = get_cart_from_session(request)
            if session_cart and session_cart.user == request.user:
                # and the session cart already belongs to us, we are done
                cart = session_cart
            elif session_cart and not session_cart.is_empty and session_cart.user != request.user:
                # if it does not belong to us yet
                database_cart = get_cart_from_database(request)
                if database_cart:
                    # and there already is a cart that belongs to us in the database
                    # delete the old database cart
                    database_cart.delete()
                # save the user to the new one from the session
                session_cart.user = request.user
                session_cart.save()
                cart = session_cart
            else:
                # if there is no session_cart, or it's empty, use the database cart
                cart = get_cart_from_database(request)
                if cart:
                    # and save it to the session
                    request.session['cart_id'] = cart.pk
        else:
            # not authenticated? cart might be in session
            cart = get_cart_from_session(request)

        if not cart:
            # in case it's our first visit and no cart was created yet
            if is_logged_in:
                cart = models.Cart(user=request.user)
            elif getattr(request, 'session', None) is not None:
                cart = models.Cart()

        if save and not cart.pk:
            cart.save()
            request.session['cart_id'] = cart.pk

        setattr(request, '_cart', cart)

    cart = getattr(request, '_cart')  # There we *must* have a cart
    return cart


def get_orders_from_request(request):
    """Return all the Orders created from the provided request."""
    orders = None
    if request.user and not request.user.is_anonymous():
        # There is a logged in user
        orders = models.Order.objects.filter(order__isnull=True, user=request.user,
                                             status__lt=models.Order.CONFIRMED)\
                                     .order_by('-created')
    else:
        order_id = getattr(request, 'session', {}).get('order_id', -1)
        orders = models.Order.objects.get(pk=order_id, status__lt=models.Order.CONFIRMED)

    return orders


def get_order_from_request(request):
    """Return the currently processing Order from a request (user session)."""
    orders = get_orders_from_request(request)
    return orders[0] if orders else None


def add_order_to_request(request, order):
    """Check that the order is linked to the current user.

    Adds the order to the session should there be no logged in user.
    """
    if request.user and not request.user.is_anonymous():
        # We should check that the current user is indeed the request's user.
        if order.user != request.user:
            order.user = request.user
            order.save()
    else:
        # Add the order_id to the session There has to be a session. Otherwise
        # it's fine to get an AttributeError
        request.session['order_id'] = order.pk

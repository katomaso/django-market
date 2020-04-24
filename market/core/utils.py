from . import models


def get_shipping_address_from_request(request):
    """Abstract the fact that users may and may not be authenticated."""
    shipping_address = None
    if request.user and not request.user.is_anonymous():
        # There is a logged-in user here, but he might not have an address
        # defined.
        try:
            shipping_address = models.Address.objects.get(
                user_shipping=request.user)
        except models.Address.DoesNotExist:
            shipping_address = None
    else:
        # The client is a guest - let's use the session instead.
        session = getattr(request, 'session', None)
        shipping_address = None
        session_address_id = session.get('shipping_address_id')
        if session is not None and session_address_id:
            shipping_address = models.Address.objects.get(pk=session_address_id)
    return shipping_address


def get_billing_address_from_request(request):
    """Abstract the fact that users may and may not be authenticated."""
    billing_address = None
    if request.user and not request.user.is_anonymous():
        # There is a logged-in user here, but he might not have an address
        # defined.
        try:
            billing_address = models.Address.objects.get(
                user_billing=request.user)
        except models.Address.DoesNotExist:
            billing_address = None
    else:
        # The client is a guest - let's use the session instead.
        session = getattr(request, 'session', None)
        session_billing_id = session.get('billing_address_id')
        if session is not None and session_billing_id:
            billing_address = models.Address.objects.get(pk=session_billing_id)
    return billing_address


def assign_address_to_request(request, address, shipping=True):
    """Set `address` as either `shipping` or billing into `request`.

    Abstract the difference between logged-in users and session-based guests.
    """
    if request.user and not request.user.is_anonymous():
        # There is a logged-in user here.
        if shipping:
            address.user_shipping = request.user
            address.save()
        else:
            address.user_billing = request.user
            address.save()
    else:
        # The client is a guest - let's use the session instead.  There has to
        # be a session. Otherwise it's fine to get an AttributeError
        if shipping:
            request.session['shipping_address_id'] = address.pk
        else:
            request.session['billing_address_id'] = address.pk


def get_user_name_from_request(request):
    """Return the username resp. '' from `request` based on user logged-in status."""
    name = ''
    if request.user and request.user.is_anonymous():
        name = request.user.get_full_name()  # TODO: Administrators!
    return name

from django.contrib.auth import get_user_model

_cache = dict()


def user():
    if not _cache.get("user"):
        _cache["user"] = get_user_model().objects.get(pk=1)
    return _cache["user"]


def vendor():
    from market.core.models import Vendor
    if not _cache.get("vendor"):
        _cache['vendor'] = Vendor.objects.get(user=user())
    return _cache['vendor']

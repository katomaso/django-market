from django.core.urlresolvers import reverse
from django.contrib.sites import shortcuts as sites


def full_url_resolver(url_name, **kwargs):
    """Add domain and protocol to the to-be-reversed ``url_name``."""
    url = sites.get_current_site().domain
    if not url.startswith("http"):
        url = "https://" + url

    if url.endswith("/"):
        url = url.rstrip("/")

    path = reverse(url_name, kwargs=kwargs)
    return url + path

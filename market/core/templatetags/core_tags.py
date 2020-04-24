# coding: utf-8
import random
import logging

from decimal import Decimal, ROUND_HALF_UP
from os import path

from django.conf import settings
from django.template import Library, loader
from django.template.defaultfilters import mark_safe
from django.utils import six
from django.utils.encoding import smart_text
from market.core import models
from market.core import menu
from urllib.parse import urlencode


register = Library()
logger = logging.getLogger(__name__)


@register.simple_tag(takes_context=True)
def add_next(context):
    """Add `next` variable into template context."""
    if "next" not in context:
        request = context['request']
        if request.GET.get("next"):
            next = request.GET.get("next")
        elif hasattr(request, "session") and request.session.get("next"):
            next = request.session.get("next")
            del request.session['next']
        else:
            next = "/"
        context["next"] = next
    return ''


@register.inclusion_tag("core/include/user-menu.html", takes_context=True)
def add_login_form(context):
    """Return LoginForm is user is not already logged in."""
    from allauth.account.forms import LoginForm
    user = context['request'].user
    if not user.is_authenticated():
        context['login_form'] = LoginForm()
        return context


@register.simple_tag(takes_context=True)
def add_menu(context, which):
    """Add "menu_items" from ``which`` menu into current context."""
    assert which in ("public", "private")
    items = getattr(menu, which)
    context['menu_items'] = items.iterator(context['request'])


@register.inclusion_tag("core/include/show-menu.html", takes_context=True)
def show_menu(context, which):
    """Generate menu items for ``which`` menu."""
    add_menu(context, which)
    return context


@register.simple_tag(takes_context=False)
def reverse(url, format="html", url_args=None, url_kwargs=None, *args, **kwargs):
    """Resolve url if possible."""
    from django.core.urlresolvers import reverse as url_reverse
    if url_args is not None:
        args.extend(url_args)
    kwargs.update(format=format)
    if url_kwargs is not None:
        kwargs.update(url_kwargs)
    return url_reverse(url, args=args, kwargs=kwargs)


@register.simple_tag(takes_context=True)
def button(context, name):
    template = loader.get_template("core/include/{0}_button.html".format(name))
    return template.render(context)


@register.inclusion_tag("core/include/search-form.html")
def search_form(term=None, **kwargs):
    kwargs.update(engine="vyrobky", term=term)
    return kwargs


class Root():
    """Holds all root elements of thecategories menu.

    Three category_list are needed
     * display all offers
     * display offers for a concrete vendor (`slug`, `category` url params)
     * display categories with vendors

    """

    def __init__(self):
        self.subcategories = []
        self.level = 0

    def __iter__(self):
        return iter(self.subcategories)


@register.inclusion_tag("core/include/category-list.html", takes_context=True)
def products_categories(context):
    return categories(context, 'products', models.Product, active=True)


@register.inclusion_tag("core/include/category-list.html", takes_context=True)
def vendors_categories(context):
    return categories(context, 'vendors', models.Vendor, active=True)


@register.inclusion_tag("core/include/category-list.html", takes_context=True)
def vendor_offers_categories(context, vendor):
    return categories(context,
                      'vendor',
                      models.Offer,
                      hide_empty=True,
                      url_kwargs={"slug": vendor.slug},
                      vendor=vendor, active=True)


@register.inclusion_tag("core/include/category-list.html", takes_context=True)
def manufacturers_categories(context):
    return categories(context, 'manufacturers', models.Manufacturer)


def categories(context, base_url, model, hide_empty=False, url_kwargs=None, **filters):
    """Build a tree of products according to their categories.

    Note either reversible_url or base_url must be specified.

    :param url_name: string -- url name to be resolved with 'category' keyword.
    :param model: a model class to count on
    :param hide_empty: if empty categories should be rendered
    :param **filters: will be used for filtering of count using QuerySet method `filter`
    """
    url_base = base_url.rstrip("/")
    items = models.Category.objects.all().order_by("ordering", "path")
    root = Root()
    cache = [root, None, None, None, None, None]  # holds parent for recursion-like algorithm
    prev_item = root

    for item in items:
        item.subcategories = []
        item.count = (model.objects
                      .filter(**filters)
                      .filter(category_id__gte=item.gte)
                      .filter(category_id__lt=item.lt)
                      .count())
        if item.level == prev_item.level:
            # just store another subitem
            cache[item.level - 1].subcategories.append(item)
        elif item.level == (prev_item.level + 1):
            # we are in sub-subtree
            cache[prev_item.level] = prev_item
            prev_item.subcategories.append(item)
        else:
            # we are back from subtree
            # for d in range(0, prev_item.level - item.level):
            #     cache[prev_item.level - d - 1].subcategories.sort(key=lambda x: x.name.lower())
            cache[item.level - 1].subcategories.append(item)
        prev_item = item
    # root.subcategories.sort(key=lambda x: x.name.lower())
    return {
        'roots': root,
        'url_base': url_base,
        'url_name': url_base,
        'url_kwargs': url_kwargs,
        'category': context.get("category"),
        'request': context["request"],
        'hide_empty': hide_empty,
    }


@register.simple_tag(takes_context=True)
def add_random_instance(context, model_name):
    """Add random instance of ``model_name`` into context as "random_<modelname>"."""
    if model_name not in ("vendor", "product", "offer", "manufacturer", "category"):
        return ""
    model_manager = getattr(models, model_name.title()).objects
    if hasattr(model_manager, "active"):
        cnt = model_manager.active().count()
        random_instance = model_manager.active()[random.randint(0, cnt - 1)] \
                          if cnt > 0 else None
    else:
        cnt = model_manager.all().count()
        random_instance = model_manager.all()[random.randint(0, cnt - 1)] \
                          if cnt > 0 else None

    context["random_" + model_name] = random_instance
    return ""


@register.simple_tag(takes_context=True)
def add_product_count(context):
    """Obtain total count of products in the system for cache key."""
    if 'product_count' not in context:
        context['product_count'] = models.Product.objects.filter(active=True).count()
    return ''


@register.simple_tag(takes_context=True)
def get_params(context, **kwargs):
    """Build a GET query string from current GET params and kwargs.

    The result can be appended behind URL path because starts with '?'
    """
    params = dict(context['request'].GET.copy().items())
    params.update(kwargs)
    return get_params_only(context, **params)


@register.simple_tag(takes_context=True)
def get_params_only(context, **params):
    """Build a GET query string from current GET params and kwargs.

    The result can be appended behind URL path because starts with '?'
    This modification will append only given parameters and discard any existing
    """
    if 'request' not in context:
        raise ValueError("Context does not have a request")
    if len(params) == 0:
        return ''
    return mark_safe(u'?{0}'.format(urlencode(params)))


@register.filter()
def as_media(image):
    """
    Transform absolute path to an image into MEDIA_URL form.

    :param value: string -- absolute path to an element
    """
    image_path = path.normpath(image.path)
    if image_path[:7] != settings.MEDIA_ROOT[:7]:
        return image_path

    image_url = image_path[len(settings.MEDIA_ROOT):].strip("/")
    return settings.MEDIA_URL + image_url


@register.simple_tag()
def lang():
    """Return current language code."""
    return settings.LANGUAGE_CODE


@register.simple_tag()
def image64(filename):
    """Print given image as base64 string."""
    out = "data:image/{};base64,".format(path.splitext(filename)[1])
    with open(filename, 'r') as f:
        out += f.read().encode("base64")
    return out


@register.filter
def as_price(price):
    """Format given Decimal to currecy string."""
    price_str = ''
    if isinstance(price, Decimal):
        price_str = smart_text(price.quantize(Decimal('1.'), rounding=ROUND_HALF_UP))
    elif isinstance(price, six.string_types):
        price_str = price
    else:
        price_str = u"{0:.0}".format(price)
    # fix spaces every 3rd place
    price_str.replace(" ", "")
    orig_len = len(price_str)
    for i in range(3, orig_len, 3):
        price_str = u" ".join((price_str[:orig_len-i], price_str[orig_len-i: orig_len-i+3]))
    return u" ".join((price_str, u"Kč"))

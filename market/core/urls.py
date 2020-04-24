# coding: utf-8
import re
from django.utils.translation import gettext as _

from market.core import menu
from market.core.views import base, admin
from urljects import U, end, slug, url

apis = []


def api(regex, view, kwargs=None, name=None):
    """Add optional 'format' into regex matching the requested format (html|json)."""
    sregex = str(regex).rstrip("$").rstrip("/")  # evaluate regex if it is not a string yet
    apis.append(sregex + ".json")
    return url(sregex + r'\.(?P<format>json|html)$', view, kwargs, name)


category = r'(?P<category>[\w\-\_\.\@\:/]*)'  # match anything acceptable in URL

urlpatterns = [
    url(U / end, base.Home, name="market-home"),
    api(U / _('product/') / slug, base.Product, name="market-product"),
    api(U / _('products/'), base.Products, name="market-products"),
    api(U / _('products/') / category, base.Products, name="market-products"),
    api(U / _('vendor/') / slug, base.Vendor, name="market-vendor"),
    api(U / _('vendor/') / slug / category, base.Vendor, name="vendor-category"),
    api(U / _('vendors/'), base.Vendors, name="market-vendors"),
    api(U / _('vendors/') / category, base.Vendors, name="vendors-category"),
    api(U / _('manufacturer/') / slug, base.Manufacturer, name="market-manufacturer"),
    api(U / _('manufacturers/'), base.Manufacturers, name="market-manufacturers"),
    api(U / _('manufacturers/') / category, base.Manufacturers, name="manufacturers-category"),
    url(U / _('ajax/validate-email'), base.validate_email, name="ajax-validate-email"),

    # custom  admin views
    url(U / _('manage/'), admin.User, name="user-manage"),
    url(U / _('manage/') / _('profile/'), admin.UserEdit, name="user-edit"),
    url(U / _('manage/') / _('my-vendor/'), admin.Home, name="admin-home"),
    url(U / _('manage/') / _('vendor/'), admin.Vendor, name="admin-vendor"),
    url(U / _('manage/') / _('close-vendor/'), admin.DeleteVendor, name="admin-vendor-delete"),
    url(U / _('manage/') / _('product/') / slug, admin.Product, name="admin-product"),
    url(U / _('manage/') / _('products/'), admin.Products, name="admin-products"),
    url(U / _('manage/') / _('add-product/'), admin.AddProduct, name="admin-product-add"),
    url(U / _('manage/') / _('add-offer/') / slug, admin.AddProduct, name="admin-offer-add"),
    url(U / _('manage/') / _('admin-ajax/products-name-hint'), admin.products_name_hint, name="admin-ajax-products-name-hint"),
    url(U / _('manage/') / _('admin-ajax/get-model-id'), admin.get_model_id, name="admin-ajax-get-model-id"),
    url(U / _('manage/') / _('admin-ajax/render-product-box'), admin.render_product_box, name="admin-ajax-render-product-box"),
    url(U / _('manage/') / _('email-confirmed/'), admin.email_confirmed, name="admin-email-confirmed"),
    url(U / _('manage/') / _('email-login/') / slug, admin.user_email_login, name="admin-email-login"),
]


class ProductsMenu(menu.MenuItem):
    title = _("Products")
    url_name = 'products'
    url_kwargs = {'format': 'html'}

    def is_selected(self, name):
        return re.match(name, '(search)?products?|home') is not None

    def is_active(self, name):
        return True


class SellersMenu(menu.MenuItem):
    title = _("Sellers")
    url_name = 'vendors'
    url_kwargs = {'format': 'html'}

    def is_selected(self, name):
        return re.match(name, 'vendor.*') is not None

    def is_active(self, name):
        return True


class ManufacturersMenu(menu.MenuItem):
    title = _("Manufacturers")
    url_name = 'manufacturers'
    url_kwargs = {'format': 'html'}

    def is_selected(self, name):
        return re.match(name, 'manufacturer.*') is not None

    def is_active(self, name):
        return True


menu.private.add_item("product", ProductsMenu())
menu.private.add_item("sellers", SellersMenu())
menu.private.add_item("manufs", ManufacturersMenu())



class CreateVendorMenuItem(menu.MenuItem):
    """MenuItem for vendor creatin."""
    url_name = "admin-vendor"
    title = _("Create Vendor")

    def is_selected(self, viewname):
        return "vendor" in viewname

    def is_active(self, request):
        if request is None:
            return True
        if request.user.is_anonymous():
            return True
        return not models.Vendor.objects.filter(user=request.user).exists()


class ManageVendorMenuItem(menu.MenuItem):
    """Manage vendor."""
    url_name = "admin-home"
    title = _("My Vendor")

    def is_selected(self, viewname):
        return "vendor" in viewname

    def is_active(self, request):
        if request is None:
            return False
        if request.user.is_anonymous():
            return False
        return not models.Vendor.objects.filter(user=request.user).exists()

menu.private.add_item('vendor-create', CreateVendorMenuItem())
menu.private.add_item('vendor-manage', ManageVendorMenuItem())

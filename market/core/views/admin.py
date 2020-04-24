# coding: utf-8
from __future__ import absolute_import
from __future__ import division

import dbmail
import json
import logging
import django.core.exceptions

from django import http
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.conf import settings
from django.dispatch import receiver
from django.db import transaction
from django.forms.models import model_to_dict
from django.forms.utils import ErrorList
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from allauth import account
from market.checkout.models import Order
from market.core import forms, models, views
from market.utils.templates import render_template

logger = logging.getLogger(__name__)


class User(views.MarketAdminView):
    """Admin view for basic profile administration."""

    def get_context_data(self, *args, **kwargs):
        """Gather non-cancelled orders."""
        user = self.request.user
        context = super().get_context_data(*args, **kwargs)
        context.update(
            object=user,
            orders=user.order_set.filter(status__lt=Order.CANCELED).order_by('created')
        )
        return context


class UserEdit(views.MarketAdminView):
    """Edit basic user info such as address."""

    def get(self, request):
        """Provide form to change address and user info."""
        context = self.get_context_data(request=request)
        shipping, billing = request.user.shipping_billing()

        # if shipping and billing are the same then dont put instance into billing form
        context.update(
            user_form=forms.UserForm(instance=request.user),
            address_form=forms.AddressesForm(
                shipping=request.user.shipping,
                billing=request.user.billing,
                billing_form_class=forms.AddressForm,
                initial={"shipping": {"name": request.user.name},
                         "billing": {"name": request.user.name}}))
        return self.render_to_response(context)

    def post(self, request):
        """Handle the forms."""
        context = self.get_context_data(request=request)
        shipping, billing = request.user.shipping_billing()

        user_form = forms.UserForm(
            instance=request.user, data=request.POST, files=request.FILES)
        address_form = forms.AddressesForm(
            instance=request.user.shipping_billing(), data=request.POST)

        context.update(
            user_form=user_form,
            address_form=address_form
        )

        if not user_form.is_valid() or not address_form.is_valid():
            return self.render_to_response(context)

        if user_form.has_changed():
            user_form.save()

        shipping, billing = address_form.save_to_request(request)

        messages.success(request, _("Data were updated"))
        return redirect("user-edit")


@receiver(account.signals.email_confirmed)
def email_confirmed_handler(sender, request, email_address, **kwargs):
    """Add email address into session to initialize the logging form with it."""
    request.session['confirmed_email'] = email_address.email


def email_confirmed(request, *args, **kwargs):
    """View to make email confirmation obvious - adds login form.

    It takes the confirmed email from session filled by the receiver above.
    """
    if request.user.is_authenticated():
        return redirect("home")
    form = account.forms.LoginForm(
        initial={'login': request.session['confirmed_email']})
    return render(request,
                  "core/private/email-confirmed.html",
                  {"form": form,
                   "email": request.session['confirmed_email'],
                   "login_url": settings.LOGIN_URL})


class Vendor(views.MarketAdminView):
    """Create a new vendor or update the current one."""

    def get(self, request, *args, **kwargs):
        """Create all necessary forms for a (new) vendor."""
        context = self.get_context_data(**kwargs)
        vendor_instance = None
        address_initial = {"address_visible": False}
        if request.user.is_authenticated():
            qs = models.Vendor.objects.filter(user=request.user, active=True)
            if qs.exists():
                vendor_instance = models.Vendor.objects.get(user=request.user, active=True)
            else:
                shipping, billing = request.user.shipping_billing()
                if billing:
                    address_initial = model_to_dict(billing)
                if shipping:
                    address_initial = model_to_dict(shipping)

        context.update(is_vendor=vendor_instance is not None)
        user_form = account.forms.SignupForm() \
                    if request.user.is_anonymous() else None
        vendor_form = forms.VendorForm(instance=vendor_instance)
        context.update({
            'user_form': user_form,
            'vendor_form': vendor_form,
            'address_form': forms.VendorAddressForm(
                prefix="address", initial=address_initial,
                instance=vendor_instance.address if vendor_instance else None),
            'position_form': forms.PositionForm(
                prefix="position", initial=address_initial,
                instance=vendor_instance.position if vendor_instance else None),
        })
        return self.render_to_response(context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Create or update vendor."""
        context = self.get_context_data(**kwargs)
        vendor_instance = None
        if request.user.is_authenticated():
            qs = models.Vendor.objects.filter(user=request.user, active=True)
            if qs.exists():
                vendor_instance = models.Vendor.objects.get(user=request.user, active=True)

        if vendor_instance and "delete" in self.POST:
            if "vendor_delete" not in request.session:
                messages.warn(_("To stop your commercial activity, press the button once more."))
                return self.get(request, *args, **kwargs)
            vendor_instance.close()
            messages.success(request, _("Your commercial activity has ended"))
            return

        user_form = None
        if request.user.is_anonymous():
            user_form = account.forms.SignupForm(request.POST, request.FILES)

        vendor_form = forms.VendorForm(
            request.POST, request.FILES, instance=vendor_instance)
        address_form = forms.VendorAddressForm(
            request.POST, prefix="address",
            instance=vendor_instance.address if vendor_instance else None)
        position_form = forms.PositionForm(
            request.POST, prefix="position",
            instance=vendor_instance.position if vendor_instance else None)

        context.update(
            user_form=user_form,
            vendor_form=vendor_form,
            address_form=address_form,
            position_form=position_form,
        )

        if ((request.user.is_anonymous() and not user_form.is_valid()) or not
            (vendor_form.is_valid() and
                address_form.is_valid() and
                position_form.is_valid())):
            if user_form and user_form._errors:
                for e in user_form._errors:
                    logger.debug("{} {}".format(e, user_form._errors[e]))
            if vendor_form._errors:
                for e in vendor_form._errors:
                    logger.debug("{} {}".format(e, vendor_form._errors[e]))
            if address_form._errors:
                for e in address_form._errors:
                    logger.debug("{} {}".format(e, address_form._errors[e]))
            messages.error(request, _("Please correct the mistakes bellow in the form"))
            return self.render_to_response(context)

        if request.user.is_anonymous():
            request.user = user_form.save(request)
        vendor = vendor_form.save(commit=False)
        vendor.user = request.user
        # to enable LOGIN_ON_EMAIL_CONFIRM
        vendor.address = address_form.save()
        if position_form.cleaned_data.get("address_visible", False):
            vendor.position = position_form.save()
        vendor.save()
        vendor_form.save_shippings()

        if vendor_instance is None:
            messages.success(request, _("Your vendor has been created!"))
            if not vendor.address.business_id:
                mail_context = {'vendor': vendor}
                dbmail.send_db_mail(
                    'core-vendor-no-id', vendor.user.email, mail_context, user=vendor.user)

        if vendor_instance is not None:
            messages.success(request, _("Changes were saved!"))

        if user_form is not None and not request.user.is_authenticated():
            account.utils.send_email_confirmation(
                request, request.user, signup=True)
            return redirect("account_email_verification_sent")
        return redirect("admin-home")


class Home(views.VendorRequiredMixin, views.MarketAdminView):
    """Dashboard showing order states and providing most common functionality."""

    def get(self, request, *args, **kwargs):
        """Get orders grouped by status."""
        context = self.get_context_data(**kwargs)
        context.update(orders_count={
            "confirming": self.vendor.orders.filter(status__lte=Order.CONFIRMING).count(),
            "confirmed": self.vendor.orders.filter(status=Order.CONFIRMED).count(),
            "completed": self.vendor.orders.filter(status=Order.COMPLETED).count(),
            "shipped": self.vendor.orders.filter(status=Order.SHIPPED).count(),
            "all": self.vendor.orders.all().count(),
        })
        context.update(orders={
            "confirmed": self.vendor.orders.filter(status=Order.CONFIRMED).order_by('-modified')[:10],
            "completed": self.vendor.orders.filter(status=Order.COMPLETED).order_by('-modified')[:10],
        })
        context.update(
            offers=models.Offer.objects.filter(
                vendor=self.vendor, active=True).order_by('-created')[:10],
            offers_count=models.Offer.objects.filter(vendor=self.vendor, active=True).count(),
            offers_deleted=models.Offer.objects.filter(
                vendor=self.vendor, active=False, removed=False).order_by('-created')[:10])
        return self.render_to_response(context)


class Product(views.VendorRequiredMixin, views.MarketFormView):
    """Create or update product - offer."""

    def dispatch(self, request, slug):
        product = get_object_or_404(models.Product, slug=slug)
        return super(Product, self).dispatch(request, product)

    def get(self, request, product):
        try:
            offer = product.offer_set.get(vendor=self.vendor)
        except models.Offer.DoesNotExist:
            offer = None
        context = self.get_context_data(product=product, offer=offer)
        context.update(offer_form=forms.OfferForm(instance=offer))
        if product.vendor == self.vendor:
            context.update(form=forms.ProductForm(instance=product))
        return self.render_to_response(context)

    def post(self, request, product):
        try:
            offer = product.offer_set.get(vendor=self.vendor)
        except models.Offer.DoesNotExist:
            offer = None
        context = self.get_context_data(product=product, offer=offer)

        if "remove" in request.POST:
            offer.remove()
            messages.info(request, _("Your offer was removed"))
            return redirect("admin-home")

        form = forms.ProductForm(data=request.POST, files=request.FILES, instance=product)
        offer_form = forms.OfferForm(data=request.POST, files=request.FILES, instance=offer)

        context.update(form=form, offer_form=offer_form)

        if product.vendor is None or product.vendor == self.vendor:
            if not form.is_valid():
                return self.render_to_response(context)
            product = form.save(commit=False)
            product.active = True
            product.vendor = self.vendor
            product.save()

        if offer_form.is_valid():
            offer = offer_form.save(commit=False)
            offer.vendor = self.vendor
            offer.product = product
            offer.active = True
            offer.save()

        if "hide" in request.POST:
            offer.hide()
            messages.info(request, _("Product was hidden"))

        return redirect("admin-home")


class Products(views.VendorRequiredMixin, views.MarketAdminView):

    def get(self, request):
        try:
            active = bool(int(request.GET.get("active", '1')))
        except ValueError:
            active = True
        context = self.get_context_data(active=active, removed=False)
        paginator, object_list = paginate(
            self.vendor.offer_set.filter(active=active, removed=False).order_by("-created"),
            request.GET, context)
        return self.render_to_response(context)


class AddProduct(views.VendorRequiredMixin, views.MarketAdminView):
    """Add product to a vendor or assign an offer to existing product."""

    template_name = "core/private/product.html"

    def get(self, request, slug=None, *args, **kwargs):
        """Give the user offer and product form to fill in."""
        context = self.get_context_data(**kwargs)
        product = None
        if slug:
            product = get_object_or_404(models.Product, slug=slug)
        context.update(
            product=product,
            form=forms.ProductForm(initial={'category': self.vendor.category}),
            offer_form=forms.OfferForm(initial={'unit_price': None,
                                                'product': product})
        )
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """Save offer and product product_form.

        Offer product_form can arrive alone since the product might have existed already.
        """
        context = self.get_context_data(**kwargs)
        if self.vendor.at_limit():
            messages.error(request, self.vendor.message["at_limit"])
            return self.get(request, *args, **kwargs)

        product_form = forms.ProductForm(request.POST, request.FILES)
        offer_form = forms.OfferForm(request.POST)
        context.update(form=product_form, offer_form=offer_form)
        product = None

        if product_form.is_valid():
            # offer product_form has to contain price
            if not offer_form.is_valid() and "unit_price" not in offer_form.cleaned_data:
                # we expect the user has selected product from dropdown
                offer_form._errors['product'] = ErrorList()
                return self.render_to_response(context)

            if self.vendor.has_limit:
                next_total = self.vendor.total + offer_form.cleaned_data['unit_price']
                if next_total > self.vendor.limit_product_total:
                    product_form.add_error(None, self.vendor.message["at_limit"])
                    return self.render_to_response(context)

                # constrain the categories for unofficial sellers to Food
                allowed_category = models.Category.objects.get(
                    name=u"Domácí", level=1)
                if product_form.cleaned_data["category"] not in allowed_category:
                    product_form.add_error(
                        "category",
                        _("You can offer only products within {!s} category").format(
                            allowed_category))
                    return self.render_to_response(context)

            try:
                product = product_form.save(commit=False)
                product.vendor = self.vendor
                product.unit_price = offer_form.cleaned_data['unit_price']
                product.save()
            except IOError:
                messages.error(request, _("Product's photo hasn't been saved due to it's invalid format"))
                product.photo = None
                product.save()

            offer_form.cleaned_data.update(vendor=self.vendor, product=product, active=True)
            models.Offer.objects.create(**offer_form.cleaned_data)
            messages.success(request, _("Product was added"))
            return http.HttpResponseRedirect(reverse("admin-home"))

        if offer_form.is_valid():
            if product is None:
                product = offer_form.cleaned_data['product']
            logger.debug("Offer form is valid")
            try:
                offer = models.Offer.objects.get(product=offer_form.cleaned_data['product'],
                                                 vendor=self.vendor)
                if not product.active:
                    product.active = True
                    product.vendor = self.vendor
                    product.save()
                for field in offer_form.cleaned_data:
                    setattr(offer, field, offer_form.cleaned_data[field])
                offer.save()
                messages.success(request, _("Old offer was updated"))
                return http.HttpResponseRedirect(reverse("admin-home"))

            except models.Offer.MultipleObjectsReturned:
                models.Offer.objects.filter(product=offer_form.cleaned_data['product'],
                                            vendor=self.vendor).delete()
            except models.Offer.DoesNotExist:
                pass

            offer = offer_form.save(commit=False)
            offer.vendor = self.vendor
            offer.active = True
            offer.save()
            messages.success(request, _("Offer to a product was added"))
            return http.HttpResponseRedirect(reverse("admin-home"))

        if offer_form.cleaned_data.get("product"):
            logger.debug("product in non valid offer form")
            product = offer_form.cleaned_data['product']
            context.update(add_offer=True, product=product)
            return self.render_to_response(context)

        logger.debug("Invalid offer form, not valid form and no product in offer form")
        del offer_form._errors['product']

        return self.render_to_response(context)


class AddOffer(views.VendorRequiredMixin, views.MarketAdminView):

    def get(self, request):
        context = self.get_context_data()
        try:
            product_id = int(request.GET['product'])
            product = models.Product.objects.get(pk=product_id)
        except (KeyError, ValueError):
            http.HttpResponse("Invalid ID")
        except models.Product.DoesNotExist:
            http.HttpResponse("Product does not exist")

        context.update(form=forms.OfferForm(initial={'product': product}))
        return self.render_to_response(context)

    def post(self, request):
        context = self.get_context_data()
        form = forms.OfferForm(request.POST, request.FILES)
        next = request.POST.get("next", None)
        if not form.is_valid():
            if next:
                messages.error(request, _("Offer was not added. Haven't you made a mistake in the form?"))
                return http.HttpResponseRedirect(next)
            context.update(form=form)
            return self.render_to_response(context)
        offer = form.save(commit=False)
        offer.vendor = self.vendor
        offer.active = True
        offer.save()
        if self.request.is_ajax():
            return http.HttpResponse(json.dumps({'status': 'success'}), content_type="application/x-javascript")
        if next:
                messages.success(request, _("Your offer was added."))
                return http.HttpResponseRedirect(next)
        return redirect("admin-home")


def products_name_hint(request):
    """Send out hints about product names."""
    data = json.parse(request.body) or request.POST
    term = data.get('term', None)
    vendor = models.Vendor.objects.get(user=request.user, active=True)
    if not term or len(term) < 4:
        return self.response(request, {'status': 'error', 'products': tuple()})
    products = models.Product.objects.filter(name__istartswith=term).exclude(vendor=vendor)
    return JsonReponse({"status": "success",
                        "products": tuple(products.values_list("name", flat=True))})

def get_model_id(request):
    data = json.parse(request.body) or request.POST
    model_name = data.get('model', None)
    safe_attrs = {}
    for k in data:
        if k in ['name', 'pk', 'id', 'slug']:
            safe_attrs[k] = data[k]

    if not model_name or len(safe_attrs) == 0:
        return JsonResponse({'status': 'error', 'id': 0})

    try:
        model = getattr(models, model_name.capitalize(), None)
        if not model:
            return JsonResponse({'status': "error", 'id': 0})
        pk = model.objects.only("pk").get(**safe_attrs).pk
        return JsonResponse({'status': 'success', 'id': pk})
    except (django.core.exceptions.FieldError,
            django.core.exceptions.ObjectDoesNotExist):
        return JsonResponse({'status': 'error', 'id': 0})


def render_product_box(request):
    data = json.parse(request.body) or request.POST
    product = None
    if "id" not in data:
        return JsonResponse({'status': 'error', 'message': _('No ID specified')})

    try:
        product = models.Product.objects.get(id=data["id"])
        vendor = models.Vendor.objects.get(user=request.user, active=True)
        if product.offer_set.filter(vendor=vendor).exists():
            return JsonResponse({'status': 'error', 'message': _('You already have an offer on this product')})
    except models.Product.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': _('No such product')})
    except KeyError:
        return JsonResponse({'status': 'error', 'message': _('Specify ID')})

    html = render_template("core/include/product-box.html",
                           {'object': product, 'no_forms_please': True},
                           request)
    return JsonResponse({'status': 'success',
                         'pk': product.pk,
                         'slug': product.slug,
                         'html': mark_safe(html)})


def confirm_email(user):
    """Utility function for confirming pripary email of a user."""
    unconfirmed_email = account.models.EmailAddress.objects.filter(
        email=user.email, user=user, verified=False)
    if unconfirmed_email.exists():
        unconfirmed_email.update(verified=True)


# @U.url_view(U.U / prihlasit / U.slug)
def user_email_login(request, slug):
    """Handle user's request of logging in via a link from their email."""
    user = request.user
    if user.is_authenticated():
        confirm_email(user)
        messages.info(request, _("You are already logged in."))
        return redirect("user-manage")

    user = get_object_or_404(models.User, uid=slug)

    if user.has_usable_password():
        messages.info(request, _("You have set up an password already. Use it for login."))
        return redirect(settings.LOGIN_URL)

    confirm_email(user)
    user = account.adapter.get_adapter(request).login(request, user)

    return redirect("account_set_password")

# coding: utf-8
import re
import logging

from decimal import Decimal
from allauth import account

from django import forms
from django.forms import widgets
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.forms.utils import ErrorList, ErrorDict

from autocomplete_light import shortcuts as autocomplete_light
from bitcategory.fields import HierarchicalField
from captcha import fields as recaptcha_fields
from market.utils.forms import (
    ModelChoiceCreationField,
    Model2CharField,
)
from market.utils.widgets import (
    CurrencyInput,
    ClearableImageInput,
)

from . import models

logger = logging.getLogger(__name__)

# register autocomplete stuff
autocomplete_light.register(
    models.Manufacturer,
    search_fields=['name', ],
    autocomplete_js_attributes={
        'minimum_characters': 3,
    },
    widget_js_attributes={
        'max_values': 6,
    }
)

autocomplete_light.register(
    models.Product,
    search_fields=['name', ],
    autocomplete_js_attributes={
        'minimum_characters': 3,
    },
    widget_js_attributes={
        'max_values': 6,
    }
)


class UserForm(forms.ModelForm):
    """Form to update basic user's information."""

    class Meta:
        """Meta."""
        fields = ("name",)
        model = models.User


class SecuredEmailForm(forms.Form):
    """Form to get contact email from the user."""
    messages = {
        "email_exists": _("Email already registered."),
        "invalid_credentials": _("Incorrect email and password combination"),
    }

    # captcha = recaptcha_fields.ReCaptchaField()
    email = forms.EmailField(required=True)
    password = forms.CharField(label=_("Password"), required=False,
                               widget=widgets.PasswordInput)

    def __init__(self, *args, **kwargs):
        """Save `request` from kwargs for optional password validation."""
        self.request = kwargs.pop('request', None)
        super(SecuredEmailForm, self).__init__(*args, **kwargs)

    def clean(self):
        """Validate whether email has not been taken yet."""
        cleaned_data = super(SecuredEmailForm, self).clean()
        user = None
        if cleaned_data.get('email'):
            if cleaned_data.get('password'):
                user = (account.adapter.get_adapter(self.request)
                                       .authenticate(
                                           self.request,
                                           email=cleaned_data['email'],
                                           password=cleaned_data['password']))
                if user is None:
                    raise ValidationError(self.messages["invalid_credentials"])

            else:  # no password
                confirmed_email = account.models.EmailAddress.objects.filter(
                    email=cleaned_data['email'])
                if confirmed_email.exists():
                    raise ValidationError(self.messages["email_exists"])
        cleaned_data["user"] = user
        return cleaned_data


class BaseSignupForm(forms.Form):
    """Serves as a base class for (allauth.)account.forms.SignupForm.

    Its only purpose is to provide `full name` field.
    """
    messages = {
        "name": _("Name is required")
    }

    name = forms.CharField(label=_("Full name"),
                           max_length=70, required=True,
                           widget=widgets.TextInput(
                               attrs={'placeholder': _('Full name'),
                                      'autofocus': 'autofocus'}))

    def signup(self, request, user):
        """Invoked at signup time to complete the signup of the user."""
        pass

    def clean(self):
        """Split name into first_name and last_name for backward compatibility."""
        cleaned_data = super().clean()
        if 'name' not in cleaned_data:
            raise ValidationError(self.messages['name'])
        cleaned_data['first_name'], cleaned_data['last_name'] = \
            cleaned_data['name'].strip().split(" ", 1)
        return cleaned_data


class AddressForm(forms.ModelForm):
    """Mandatory address form."""

    class Meta:
        """Meta."""
        model = models.Address
        exclude = ("user_shipping", "user_billing", "state", "position", "position_x", "position_y")
        widgets = {
            "extra": forms.Textarea(attrs={"cols": 23, "rows": 5})
        }


class PositionForm(forms.ModelForm):
    """It is an Address form with fields necessary for location and is optional."""

    address_visible = forms.BooleanField(label=_("I have a physical vendor."),
                                         required=False)

    class Meta:
        """Meta."""
        model = models.Address
        exclude = ("user_shipping", "user_billing", "state",
                   "name", "business_id", "tax_id", "zip_code")
        widgets = {
            'position': forms.HiddenInput,
            'position_x': forms.HiddenInput,
            'position_y': forms.HiddenInput,
        }

    class Media:
        """Media."""
        js = ('https://api4.mapy.cz/loader.js', )

    def is_valid(self):
        """Decide whether to clean form based on visibility of the address."""
        if not hasattr(self, "cleaned_data"):
            self.full_clean()
        if not self.cleaned_data.get("address_visible", False):
            return True
        return super(PositionForm, self).is_valid()

    def clean(self):
        data = self.cleaned_data
        if not data["address_visible"]:
            self._errors = ErrorDict()
        return data


class VendorAddressForm(forms.ModelForm):
    """Vendor address has more mandatory field than generic address."""

    name = forms.CharField(max_length=255, required=True, label=_("Name"))
    business_id = forms.CharField(max_length=10, required=False, label=_("Business number"))
    tax_id = forms.CharField(max_length=12, required=False, label=_("Tax ID"))
    zip_code = forms.CharField(max_length=10, required=True, label=_("Zip code"))

    class Meta:
        model = models.Address
        exclude = ("user_shipping", "user_billing", "state", "position", "position_x", "position_y")


class VendorForm(forms.ModelForm):
    """Form for creating and updating Vendor."""

    category = HierarchicalField(queryset=models.Category.objects.all(), label=_("Category"))

    bank_account = Model2CharField(
        models.BankAccount, max_length=30, label=_("Bank account"), required=False)

    _messages = {
        "bank_account_number": _("Bank account number should be PREFIX - NUMBER / BANK"),
    }

    class Meta:
        """Define model and fields to be handled."""
        model = models.Vendor
        fields = ("name", "category", "motto", "description", "ships", "logo", "openings", "bank_account")
        widgets = {
            'description': forms.Textarea(attrs={"class": "input-xxlarge"}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize M2M with all possibilities."""
        kwargs.update(prefix="vendor")
        super(VendorForm, self).__init__(*args, **kwargs)

    def clean_bank_account(self):
        """Parse bank account number and construct an instance of BankAccount model."""
        if not self.cleaned_data.get('bank_account'):
            return None

        number = self.cleaned_data['bank_account']
        match_o = re.match(r'(?:(\d+)\s*\-\s*)?(\d+)\s*/\s*(\d{4})', number)
        if match_o is None:
            raise ValidationError(self._messages["bank_account_number"])
        try:
            int(match_o.group(2))
        except:
            raise ValidationError(self._messages["bank_account_number"])

        try:
            bank_account = self.instance.bank_account
            bank_account.prefix = match_o.group(1)
            bank_account.number = match_o.group(2)
            bank_account.bank = match_o.group(3)
            bank_account.save()
        except:
            bank_account = models.BankAccount.objects.create(
                prefix=match_o.group(1), number=match_o.group(2), bank=match_o.group(3))

        return bank_account


class ProductForm(forms.ModelForm):
    """Add product to a vendor."""

    name = forms.CharField(
        widget=autocomplete_light.TextWidget(
            'ProductAutocomplete',
            attrs={"placeholder": _("select your product if we already know it")}),
        required=True, label=_("Name"))
    category = HierarchicalField(queryset=models.Category.objects.all(), label=_("Category"))
    manufacturer = ModelChoiceCreationField(
        label=_("Manufacturer"),
        queryset=models.Manufacturer.objects.all(),
        to_field_name="name", required=False,
        widget=autocomplete_light.TextWidget(
            'ManufacturerAutocomplete',
            attrs={"placeholder": _("select the manufacturer if we already know them")}))

    class Meta:
        model = models.Product
        fields = ("name", "category", "description", "manufacturer",
                  "photo", "expedition_days", "tax")
        widgets = {
            'description': forms.Textarea,
            'extra': forms.Textarea,
            "photo": ClearableImageInput,
        }


class OfferForm(forms.ModelForm):

    class Meta:
        model = models.Offer
        fields = ("product", "unit_price", "note", "shipping_price")
        widgets = {
            'product': forms.HiddenInput,
            'unit_price': CurrencyInput,
            'shipping_price': CurrencyInput,
            'note': widgets.TextInput,
        }

    class Media:
        js = list()

    def clean_shipping_price(self):
        shipping_price = self.cleaned_data.get('shipping_price', '')
        if not shipping_price:
            return Decimal('0.00')
        return Decimal(shipping_price)

    def _post_clean(self):
        try:
            return super(OfferForm, self)._post_clean()
        except ValueError:
            self._errors['product'] = ErrorList([_("Field is required"), ])


class AddressesForm(forms.Form):
    """Uberform which manages shipping and billing addresses.

    It provides the option for the addresses to be the same.

    You can pass `billing` (resp. `shipping`) models instances to edit them.
    You can pass your own `billing_form_class` and `shipping_form_class` which
    have to be `ModelForm` subclasses.

    Validity of empty form is controlled by a checkbox field `necessary`. If the
    addresses are not necessary then forms data "shipping" and "billing" will
    be always empty dictionaries.

    This form contains one own field - `addresses_the_same` and two subforms -
    `billing`, `shipping`
    """
    error_messages = {
        'empty': _('Shipping address has to be filled when marked different'),
        'required': _('Billing address is required')
    }

    necessary = forms.BooleanField(
        label=_("Mark whether address is necessary"), required=False, initial=False)

    addresses_the_same = forms.BooleanField(
        label=_("Shipping is the same as billing"), required=False, initial=True)

    def __init__(self, data=None, files=None, billing=None, shipping=None,
                 billing_form_class=None, shipping_form_class=None,
                 auto_id='id_%s', prefix=None, initial={}, error_class=ErrorList,
                 label_suffix=None):
        """Initialize with two addresses for billing and shipping."""
        super(AddressesForm, self).__init__(data, files,
                                            initial={"addresses_the_same": (shipping == billing)},
                                            label_suffix=label_suffix)
        assert billing_form_class is not None or shipping_form_class is not None

        #  TODO: construct a ModelForm from Address model instance
        bform = (billing_form_class or shipping_form_class)
        sform = (shipping_form_class or billing_form_class)

        self.billing = bform(data, files, instance=billing, prefix="billing",
                             initial=initial.pop("billing", None), label_suffix=label_suffix)

        self.shipping = sform(data, files, prefix="shipping",
                              instance=shipping if shipping != billing else None,
                              initial=initial.pop("shipping", None), label_suffix=label_suffix)

        self.billing_empty = False  # helper in save method (bcs Form does not have is_empty method)

    def clean(self):
        """The form is valid even when both addresses are empty."""
        data = self.cleaned_data
        is_necessary = data.get('necessary', False)

        # Billing is required (if `is_necessary`)
        if is_necessary and not self.billing.is_valid():
            raise ValidationError(self.error_messages['required'])

        # User marks addresses as different - check they both are valid
        if is_necessary and not data.get('addresses_the_same', True):
            if not all((self.shipping.is_valid(), self.billing.is_valid())):
                raise ValidationError(self.error_messages['empty'])

        # Mark as valid in case no addresses are necessary
        if not is_necessary:
            self.billing._errors = ErrorDict()
            self.shipping._errors = ErrorDict()

        data['billing'] = getattr(self.billing, "cleaned_data", {})
        data['shipping'] = getattr(self.shipping, "cleaned_data", {})

        return data

    def save(self, commit=True):
        """Return tuple with address models.

        In the case when empty form was allowed (`required=False` in the constructor)
        tuple `(None, None)` might be returned.
        """
        billing = None
        shipping = None

        if not self.cleaned_data['necessary']:
            return (billing, shipping)

        billing = self.billing.save(commit=commit)

        if self.cleaned_data['addresses_the_same']:
            shipping = billing
        else:
            if billing.user_shipping is not None:
                billing.user_shipping = None
                billing.save()
            shipping = self.shipping.save(commit=commit)
        return (billing, shipping)

    def save_to_request(self, request):
        if request.user.is_authenticated():
            billing, shipping = self.save(commit=False)
            if shipping:
                shipping.user_shipping = request.user
                if not shipping.name:
                    shipping.name = request.user.get_full_name()
                if shipping != billing:
                    # reset billing address because it could have changed
                    shipping.user_billing = None
                shipping.save()
            if billing:
                billing.user_billing = request.user
                if not billing.name:
                    billing.name = request.user.get_full_name()
                billing.save()
        else:
            billing, shipping = self.save(commit=True)
            if shipping:
                request.session['shipping_address_id'] = shipping.pk
            if billing:
                request.session['billing_address_id'] = billing.pk
        return billing, shipping

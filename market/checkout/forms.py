# coding: utf-8
from django import forms
from django.utils.translation import ugettext as _
from market import app_settings

from . import models


class ShippingFormSet(forms.BaseModelFormSet):
    """Form to (un)select shipping for every suborder."""

    messages = {
        "no-shipping": _("You selected shipping for a vendor which does not provide shipping.")
    }

    class Meta:
        """Define model forms vitals."""
        model = models.Order
        fields = ["shipping", "message"]
        can_delete = False
        extra = 0

    def clean(self):
        """Check that nobody ordered shipping when it is not available."""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        if any(form.cleaned_data['shipping'] and not form.instance.vendor.ships
               for form in self.forms):
            raise forms.ValidationError(self.messages['no-shipping'])


class PaymentForm(forms.Form):
    """Form provides all possible payment methods."""

    payment = forms.ModelChoiceField(
        queryset=models.PaymentBackend.objects.filter(active=True),
        widget=forms.RadioSelect,
        empty_label=_("Pay on delivery") if app_settings.EMPTY_PAY_ON_DELIVERY else None,
        label=_("Payment"))


class CartItemForm(forms.ModelForm):
    """A form for the CartItem model. To be used in the CartDetails view."""

    quantity = forms.IntegerField(min_value=0, max_value=9999)

    class Meta:
        """Set attributes of the Model Form."""
        model = models.CartItem
        fields = ['quantity', ]

    def save(self, *args, **kwargs):
        """Use Cart's own method `update_quantity`."""
        quantity = self.cleaned_data['quantity']
        instance = self.instance.cart.update_quantity(self.instance.pk, quantity)
        return instance


def get_cart_item_formset(cart_items, data=None):
    """Return a CartItemFormSet which can be used in the CartDetails view.

    :param cart_items: The queryset to be used for this formset. This should
      be the list of updated cart items of the current cart.
    :param data: Optional POST data to be bound to this formset.
    """
    formset_factory = forms.modelformset_factory(
        models.CartItem, extra=0, fields=["quantity", "id"])
    form_set = formset_factory(data, queryset=cart_items)

    # The Django ModelFormSet pulls the item out of the database again and we
    # would lose the updated subtotals
    for form in form_set:
        for cart_item in cart_items:
            if form.instance.pk == cart_item.pk:
                form.instance = cart_item
    return form_set

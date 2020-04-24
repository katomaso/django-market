# coding: utf-8
from django import forms
from django.forms import widgets
from django.utils import timezone
from django.utils.translation import ugettext as _

from market.tariff.models import Billing, Campaign


class CampaignForm(forms.Form):
    """Form to obtain a discount through promotion code."""

    code = forms.CharField(max_length=8)
    code_errors = {
        "expired": _("This code has expired."),
        "overused": _("This code is used up."),
        "invalid": _("This code does not exist."),
        # check abusing = double-usage in the view where we have the user's vendor
    }

    def clean_code(self):
        """Check for existence of the model and validity of an instance."""
        code = self.cleaned_data["code"].upper()
        qs = Campaign.objects.filter(code=code)
        if not qs.exists():
            raise forms.ValidationError(self.code_errors["invalid"])
        if not qs.filter(usages__gt=0).exists():
            raise forms.ValidationError(self.code_errors["overused"])
        if not qs.filter(expiration__gt=timezone.now()).exists():
            raise forms.ValidationError(self.code_errors["expired"])
        self.cleaned_data["campaign"] = qs.get()
        return self.cleaned_data


class BillingForm(forms.ModelForm):
    """Form to set-up vendor's Billing."""

    class Meta:
        """Setup only billing period."""

        model = Billing
        fields = ('next_period', )
        widgets = {'next_period': widgets.RadioSelect}

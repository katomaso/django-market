# coding:utf-8
import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.http import Http404

from urljects import URLView, U

from market.core.views import (VendorRequiredMixin,
                                  MarketListView,
                                  MarketAdminView)
from . import models, forms

logger = logging.getLogger(__name__)


class TariffList(MarketListView, URLView):
    """Render list of all tariffs."""

    url = U / _(r'tariff.html')
    url_name = 'tariff-list'

    model = models.Tariff


class TariffManage(VendorRequiredMixin, MarketAdminView, URLView):
    """Allow change of billing period."""

    url = U / _('tariff/') / _('manage.html')
    url_name = 'tariff-manage'

    def post(self, request):
        """Handle form data."""
        context = self.get_context_data()
        if "tariff" in request.POST:
            return self._process_tariff(request, context)
        elif "code" in request.POST:
            return self._process_campaign(request, context)
        logger.error("Missing keys 'tariff' or 'code' in form data {!s}".format(request.POST))
        raise Http404(_("Whoops! This shouldn't have happened. Please contact administrator"))

    def _process_campaign(self, request, context):
        """Validate double spend of the code and assign dicount to a vendor."""
        form = forms.CampaignForm(data=request.POST)

        if form.is_valid():
            campaign = form.cleaned_data["campaign"]
            try:
                # make sure that current vendor didn't use the campaign twice
                campaign.use(self.vendor)
                messages.success(request, _("You got a discount: " + str(campaign.discount)))
            except ValueError as error:
                messages.error(request, error.message)
            return redirect("tariff-manage")

        context.update(campaign_form=form)
        return self.render_to_response(context)

    def _process_tariff(self, request, context):
        form = forms.BillingForm(
            data=request.POST,
            instance=models.Billing.objects.get(vendor=self.vendor))
        if form.is_valid():
            form.save()
            messages.success(request, _("Settings saved"))
            return redirect('tariff-manage')

        context.update(form=form)
        return self.render_to_response(context)

    def get_context_data(self, *args, **kwargs):
        """Add tariff models to the context."""
        ctx = super().get_context_data(*args, **kwargs)
        vendor_billing = models.Billing.objects.get(vendor=self.vendor)
        ctx.update(
            bills=models.Bill.objects.filter(vendor=self.vendor).order_by('-created'),
            discounts=models.Discount.objects.filter(vendor=self.vendor).order_by('-usages'),
            form=forms.BillingForm(instance=vendor_billing),
            campaign_form=forms.CampaignForm(),
            campaign_active=models.Campaign.objects.filter(
                usages__gt=0, expiration__gt=timezone.now()).exists(),
            billing=vendor_billing,
            today=timezone.now().date())
        return ctx

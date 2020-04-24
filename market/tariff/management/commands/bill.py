# coding: utf-8
from datetime import date
from django.core.management.base import BaseCommand

from market.tariff.models import Billing


class Command(BaseCommand):
    args = ''
    help = 'Issue billing of the customers which has entered billing period'

    def handle(self, *args, **options):
        billings = Billing.objects.filter(next_bill__lte=date.now(), active=True)
        for billing in billings:
            billing.bill()

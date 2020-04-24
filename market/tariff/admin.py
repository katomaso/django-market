from auditlog.registry import auditlog
from django.contrib import admin

from . import models

auditlog.register(models.Discount)
auditlog.register(models.Campaign)


class StatisticsAdmin(admin.ModelAdmin):
    """Display usage statistics."""

    list_display = ('vendor', 'quantity', 'price', 'tariff', 'created')
    list_filter = ('vendor',)
    search_fields = ('vendor',)
    ordering = ('vendor', 'created')


class CampaignAdmin(admin.ModelAdmin):
    """Manage campaigns."""

    list_display = ('usages', 'used', 'expiration', 'discount')
    list_filter = ('usages', 'expiration')


admin.site.register(models.Tariff, admin.ModelAdmin)
admin.site.register(models.Billing, admin.ModelAdmin)
admin.site.register(models.Statistics, StatisticsAdmin)
admin.site.register(models.Campaign, CampaignAdmin)

from auditlog.registry import auditlog
from django.contrib import admin

from . import models

auditlog.register(models.Cart)
auditlog.register(models.CartItem)
auditlog.register(models.Order)
auditlog.register(models.OrderItem)


class OrderInlineAdmin(admin.TabularInline):
    model = models.Order
    fk_name = "order"
    fields = ('uid', 'vendor', 'status', 'total')
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    # form = UserChangeForm
    # add_form = UserCreationForm
    # change_password_form = AdminPasswordChangeForm
    fields = ['user', 'status',
              ('total', 'subtotal'),
              ('modified', 'created'),
              ('billing_address_text', 'shipping_address_text'),
              ]
    list_display = ('uid', 'modified', 'user', 'status', 'total', 'amount_paid')
    list_filter = ('status', )
    search_fields = ('user', )
    ordering = ('-created', 'status', 'user')
    readonly_fields = ('billing_address_text',
                       'shipping_address_text',
                       'created',
                       'modified')
    inlines = [OrderInlineAdmin]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(order__isnull=True)


class CartItemInlineAdmin(admin.TabularInline):
    model = models.CartItem
    fk_name = 'cart'


class CartAdmin(admin.ModelAdmin):
    model = models.Cart
    list_display = ('id', 'user', 'modified', 'total_quantity')
    inlines = (CartItemInlineAdmin, )


admin.site.register(models.PaymentBackend, admin.ModelAdmin)

admin.site.register(models.Order, OrderAdmin)
admin.site.register(models.Cart, CartAdmin)

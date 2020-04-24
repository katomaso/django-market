# coding: utf-8
from auditlog.registry import auditlog

from django import forms
from django.contrib import admin
from allauth.account import models as account_models
from . import models


auditlog.register(models.User, exclude_fields=['uid', ])
auditlog.register(account_models.EmailAddress)
auditlog.register(models.Address)
auditlog.register(models.BankAccount)

auditlog.register(models.Vendor)
auditlog.register(models.Offer)
auditlog.register(models.Product)


# TODO: find out what it is
class LocalizeDecimalFieldsForm(forms.ModelForm):
    """Localize Decimal field names."""

    def __new__(cls, *args, **kwargs):
        new_class = super(LocalizeDecimalFieldsForm, cls).__new__(cls)
        if hasattr(new_class, 'base_fields'):
            for field in list(new_class.base_fields.values()):
                if isinstance(field, (forms.DecimalField, forms.FloatField)):
                    field.localize = True
                    field.widget.is_localized = True
        return new_class


# TODO: find out what it is
class LocalizeDecimalFieldsMixin(object):
    """Localize input fields for models of type DecimalField in the admin interface.

    To be used as a mixin for classes derived from admin.ModelAdmin, admin.TabularInline ...
    If your class derived from ModelAdmin wants to override the form attribute,
    make sure that this form is derived from LocalizeDecimalFieldsForm and not
    from forms.ModelForm.
    """
    form = LocalizeDecimalFieldsForm


class UserAdmin(admin.ModelAdmin):
    add_form_template = 'admin/auth/user/add_form.html'
    change_user_password_template = None
    fieldsets = (
        (None, {'fields': ('name', 'email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}),
    )
    # form = UserChangeForm
    # add_form = UserCreationForm
    # change_password_form = AdminPasswordChangeForm
    list_display = ('email', 'name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('name', 'email')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(UserAdmin, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """Use special form during user creation."""
        defaults = {}
        if obj is None:
            defaults.update({
                'form': self.add_form,
                'fields': admin.util.flatten_fieldsets(self.add_fieldsets),
            })
        defaults.update(kwargs)
        return super(UserAdmin, self).get_form(request, obj, **defaults)


class CategoryInlineAdmin(admin.TabularInline):
    readonly_fields = ('id', 'path')
    model = models.Category
    fk_name = "parent"
    prepopulated_fields = {
        'slug': ('name', )
    }


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'path')
    readonly_fields = ('id', 'path')
    inlines = (CategoryInlineAdmin, )
    prepopulated_fields = {
        'slug': ('name', )
    }


class OfferAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'unit_price', 'active')


class OfferAdminInline(admin.TabularInline):
    model = models.Offer


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'price', 'active', 'sold')
    exclude = ('slug', 'rating_score', 'rating_votes', 'sold')
    inlines = [OfferAdminInline]


class ProductAdminInline(admin.TabularInline):
    model = models.Product
    list_display = ('name', 'price', 'active', 'sold', 'rating')


class VendorAdmin(admin.ModelAdmin):
    model = models.Vendor
    list_display = ('name', 'user', 'active')
    inlines = [
        ProductAdminInline,
        OfferAdminInline
    ]


admin.site.register(models.User, UserAdmin)

admin.site.register(models.Product, ProductAdmin)
admin.site.register(models.Offer, OfferAdmin)
admin.site.register(models.Category, CategoryAdmin)

admin.site.register(models.BankAccount, admin.ModelAdmin)
admin.site.register(models.Address, admin.ModelAdmin)

admin.site.register(models.Vendor, VendorAdmin)

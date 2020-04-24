# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-31 10:29
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models

import django.db.models.deletion
import django.core.validators

from django.utils.translation import gettext as _


class Migration(migrations.Migration):

    dependencies = [
        ('invoice', '__first__'),
        ('market', '0001_initial'),
        ('sites', '__latest__'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentbackend',
            name='vendor',
            field=models.ManyToManyField(through='market.VendorPayment', to='market.Vendor'),
        ),
        migrations.AddField(
            model_name='product',
            name='vendor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='market.Vendor'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='market.Offer', verbose_name=_('Item')),
        ),
        migrations.AddField(
            model_name='order',
            name='cart',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='market.Cart'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_backend',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='market.PaymentBackend'),
        ),
        migrations.AddField(
            model_name='order',
            name='proforma',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='invoice.Invoice'),
        ),
        migrations.AddField(
            model_name='order',
            name='invoice',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='invoice.Invoice'),
        ),
        migrations.AddField(
            model_name='order',
            name='vendor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='market.Vendor'),
        ),
        migrations.AddField(
            model_name='order',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name=_('User')),
        ),
        # migrations.AddField(
        #     model_name='user',
        #     name='site',
        #     field=models.ForeignKey('sites.Site', default=settings.SITE_ID),
        # ),
        migrations.AddField(
            model_name='offer',
            name='product',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='market.Product'),
        ),
        migrations.AddField(
            model_name='offer',
            name='vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='market.Vendor'),
        ),
        migrations.AddField(
            model_name='vendorpayment',
            name='vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_backend', to='market.Vendor'),
        ),
        migrations.AddField(
            model_name='extraorderpricefield',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='market.Order', verbose_name=_('Order')),
        ),
        migrations.AddField(
            model_name='extraorderitempricefield',
            name='order_item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='market.OrderItem', verbose_name=_('Order item')),
        ),
        migrations.AddField(
            model_name='cartitem',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='market.Offer'),
        ),
        migrations.AddField(
            model_name='address',
            name='user_billing',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='billing_address', to=settings.AUTH_USER_MODEL, verbose_name=_('Billing')),
        ),
        migrations.AddField(
            model_name='address',
            name='user_shipping',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='shipping_address', to=settings.AUTH_USER_MODEL, verbose_name=_('Shipping')),
        ),
        migrations.AddField(
            model_name='statistics',
            name='tariff',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='market.Tariff'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='discount',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='market.Discount'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='vendors',
            field=models.ManyToManyField(to='market.Vendor'),
        ),
    ]

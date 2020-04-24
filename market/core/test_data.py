# coding: utf-8
import os
from os import path
import random
import logging

from decimal import Decimal
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from ratings.models import Vote, Score

from . import models

logger = logging.getLogger(__name__)


@transaction.atomic
def load():
    """Load testing data into database & media."""
    users = []
    user, created = models.User.objects.get_or_create_verified(
        email="pan@a.cz", defaults={
            'name': "Pan A",
            "password": "ahoj",
        })
    users.append(user)
    user, created = models.User.objects.get_or_create_verified(
        email="pan@b.cz", defaults={
            "name": "Pan B",
            "password": "ahoj",
        })
    users.append(user)
    user, created = models.User.objects.get_or_create_verified(
        email="pan@c.cz", defaults={
            "name": "Pan C",
            "password": "ahoj",
        })
    users.append(user)
    user, created = models.User.objects.get_or_create_verified(
        email="pan@d.cz", defaults={
            "name": "Pan D",
            "password": "ahoj",
        })
    users.append(user)
    user, created = models.User.objects.get_or_create_verified(
        email="pan@e.cz", defaults={
            "name": "Pan E",
            "password": "ahoj",
        })
    users.append(user)

    # own data load
    image_dir = os.path.join(settings.APP_ROOT, "core", 'test_data')
    zvirata = models.Category.objects.get(name="Chovatelství")
    zvirata_uzitkova = models.Category.objects.get(name="Užitková zvířata")
    auto_moto = models.Category.objects.get(name="Auto & Moto")
    logger.info("Loading core.load.adresses")
    addresses = []
    addresses.append(models.Address.objects.get_or_create(
        name="Pan A",
        defaults={
            "city": "Praha 1",
            "country": "Pha",
            "user_shipping": users[0],
            "street": "Zborovská 15",
            "user_billing": users[0],
            "zip_code": "110 00",
            "business_id": "123445678",
            "tax_id": "CZ123445678"
        })[0])
    addresses.append(models.Address.objects.get_or_create(
        name="Pan A pozice",
        defaults={
            "city": "Brno",
            "country": "Brn",
            "user_shipping": None,
            "street": "Nádražní 1",
            "position_x": "16.6104591",
            "position_y": "49.1908406",
            "user_billing": None,
            "zip_code": "602 00",
            "business_id": None,
            "tax_id": None,
        })[0])
    addresses.append(models.Address.objects.get_or_create(
        name="Pan B",
        defaults={
            "city": "Praha 1",
            "country": "Pha",
            "user_shipping": users[1],
            "street": "Holečkova 16",
            "user_billing": users[1],
            "zip_code": "110 00",
            "business_id": "123345678",
            "tax_id": "CZ123345678"
        })[0])
    addresses.append(models.Address.objects.get_or_create(
        name="Pan B pozice",
        defaults={
            "city": "Praha 1",
            "country": "Pha",
            "user_shipping": None,
            "state": None,
            "street": "Holečkova 16",
            "position_x": "14.394821011979426",
            "position_y": "50.074210901632355",
            "user_billing": None,
            "zip_code": "110 00",
            "business_id": None,
            "tax_id": None,
        })[0])
    addresses.append(models.Address.objects.get_or_create(
        name="Pan C",
        defaults={
            "city": "Praha 3",
            "country": "Pha",
            "user_shipping": users[2],
            "street": "Ruská 32",
            "user_billing": users[2],
            "zip_code": "120 00",
            "business_id": "123456678",
            "tax_id": "CZ123456678"
        })[0])
    addresses.append(models.Address.objects.get_or_create(
        name="Pan D",
        defaults={
            "city": "Praha 3",
            "country": "Pha",
            "user_shipping": users[3],
            "state": None,
            "street": "Myslíkova 3",
            "user_billing": users[3],
            "zip_code": "130 00",
            "business_id": "112345678",
            "tax_id": "CZ112345678",
        })[0])
    addresses.append(models.Address.objects.get_or_create(
        name="Pan E",
        defaults={
            "city": "Praha 4",
            "country": "Pha",
            "user_shipping": users[4],
            "state": None,
            "street": "Pertoldova 223",
            "user_billing": users[4],
            "zip_code": "141 00",
            "business_id": "127976543",
            "tax_id": "CZ782635429",
        })[0])
    addresses.append(models.Address.objects.get_or_create(
        name="Pan E pozice",
        defaults={
            "city": "Praha 4",
            "country": "Pha",
            "user_shipping": None,
            "state": None,
            "street": "Pertoldova 223",
            "position_x": "14.404821011979426",
            "position_y": "50.056210901632355",
            "user_billing": None,
            "zip_code": "141 00",
            "business_id": None,
            "tax_id": None,
        })[0])
    logger.info("core.load.accounts")
    accounts = [
        models.BankAccount.objects.get_or_create(**kwargs)[0]
        for kwargs in (
            dict(number=Decimal("1122234566"),
                 defaults=dict(bank=Decimal("6250"), prefix=Decimal("638424"))),
            dict(number=Decimal("1764294723"),
                 defaults=dict(bank=Decimal("6250"))),
            dict(number=Decimal("4455667788"),
                 defaults=dict(bank=Decimal("1234"))),
            dict(number=Decimal("9876543521"),
                 defaults=dict(bank=Decimal("6250"))))
    ]

    logger.info("core.load.vendors")
    vendors = []
    vendor, created = models.Vendor.objects.get_or_create(name="Obchod pana A", defaults={
        "category": zvirata,
        "bank_account": accounts[0],
        "motto": "Best store in N.Y.",
        "user": users[0],
        "address": addresses[0],
        "position": addresses[1],
        "active": True,
    })
    if created:
        vendor.background = SimpleUploadedFile(name='vendorA_background.jpeg', content_type='image/jpeg',
                                             content=open(path.join(image_dir, 'vendorA_background.jpeg'), 'rb').read())
        vendor.save()
    vendors.append(vendor)

    vendor, created = models.Vendor.objects.get_or_create(name="Obchod pana B", defaults={
        "category": zvirata,
        "bank_account": accounts[1],
        "motto": "Prodáváme jen přátelská zvířátka",
        "user": users[1],
        "address": addresses[2],
        "position": addresses[3],
        "active": True,
    })
    vendors.append(vendor)

    vendor, created = models.Vendor.objects.get_or_create(name="Obchod pana E", defaults={
        "category": auto_moto,
        "bank_account": accounts[3],
        "motto": "Žádný dovoz z Číny. Pravá česká práce.",
        "description": """Vyrábíme elektromobily již 3 dny. Jsme nejstarší výrobce
        elektromobilů v České Republice.
        Samozřejmě jsme jednička v oboru a tesla Motors se proti nám může jít zakopat.""",
        "user": users[4],
        "address": addresses[5],
        "position": addresses[6],
        "active": True,
    })
    vendors.append(vendor)

    # load manufacturers
    print("core.load.manufacturers")
    klimatex = models.Manufacturer.objects.get_or_create(
        name="Klimatex",
        description="Výrobce vysoce kvalitního funkčního prádla.",
        defaults={"category": models.Category.objects.get(name="Oblečení a Obuv"), "email": "zakaznik@klimatex.cz"})[0]
    skoda = models.Manufacturer.objects.get_or_create(
        name="Škoda Auto",
        description="Tradiční český výrobce automobilů, aktuálně vlastněný německou společností Lidový vůz, ale přesto stále vyrábějcí v Mladé Boleslavi.",
        defaults={"category": models.Category.objects.get(name="Automobily"), "email": "zakaznik@skoda.cz"})[0]

    print("core.load.products and offers")
    products = []
    product, created = models.Product.objects.get_or_create(name="Houpaci kocicka pro nejmensi", vendor=vendors[0], defaults={
        "category": zvirata_uzitkova,
        "description": "Barvy testované, netoxické. Lze žužlat.",
        "price": Decimal("10000.00"),
        "editable": False,
        "active": True,
        "manufacturer": skoda,
    })

    if created:
        product.photo = SimpleUploadedFile(
            name="product_photo.jpeg", content_type="image/jpeg",
            content=open(path.join(image_dir, "photo_1.jpeg"), "rb").read())
        product.save()

        models.Offer.objects.get_or_create(vendor=vendors[0], product=product, defaults={
            "unit_price": Decimal("10000.00"),
            "shipping_price": Decimal("1000.00"),
            "active": True,
        })
    else:
        models.Offer.objects.filter(name=product.name).update(product=product, vendor=vendors[0])
    products.append(product)
    product, created = models.Product.objects.get_or_create(name="Sandalky", vendor=vendors[1], defaults={
        "category": models.Category.objects.get(path="obleceni-a-obuv/damska-obuv/sandaly"),
        "description": "Kolekce Galex pro rok 2014.",
        "extra": "barva: barevná",
        "editable": False,
        "active": True,
        "price": Decimal("10000.00"),
        "sold": 4,
    })
    if created:
        product.photo = SimpleUploadedFile(
            name="product_photo.jpeg", content_type="image/jpeg",
            content=open(path.join(image_dir, "photo_2.jpeg"), "rb").read())
        product.save()

        models.Offer.objects.get_or_create(vendor=vendors[1], product=product, defaults={
            "unit_price": Decimal("1200.00"),
            "quantity": 5,
            "shipping_price": Decimal("150.00"),
            "active": True,
            "sold": 4,
        })
    else:
        models.Offer.objects.filter(name=product.name).update(product=product, vendor=vendors[1])
    products.append(product)

    product, created = models.Product.objects.get_or_create(name="Trezor na dokumenty AAE736", vendor=vendors[0], defaults={
        "category": zvirata_uzitkova,
        "description": "Nenápadný trezor ve velikosti běžného obrazu. S kodovým mechanickým zámkem a výbušnou pojistkou pro velký úspěch z palestinské ambasády.",
        "extra": "barva: růžová\nváha: 100kg",
        "editable": False,
        "active": True,
        "price": Decimal("10000.00"),
        "sold": 3,
    })
    if created:
        product.photo = SimpleUploadedFile(
            name="product_photo.jpeg", content_type="image/jpeg",
            content=open(path.join(image_dir, "photo_3.jpeg"), "rb").read())
        product.save()

        models.Offer.objects.get_or_create(vendor=vendors[0], product=product, defaults={
            "unit_price": Decimal("5500.00"),
            "shipping_price": Decimal("300.00"),
            "active": True,
            "sold": 1,
        })
        models.Offer.objects.get_or_create(vendor=vendors[1], product=product, defaults={
            "unit_price": Decimal("5300.00"),
            "shipping_price": Decimal("400.00"),
            "active": True,
            "quantity": 3,
            "sold": 2,
        })
    else:
        models.Offer.objects.filter(name=product.name, sold=1).update(product=product, vendor=vendors[0])
        models.Offer.objects.filter(name=product.name, sold=2).update(product=product, vendor=vendors[1])
    products.append(product)

    product, created = models.Product.objects.get_or_create(name="Ochočená sova", vendor=vendors[2], defaults={
        "category": zvirata_uzitkova,
        "description": "Sova lepší než kočka! Myši chytá taky a zároveň v noci hlídá váš domov.",
        "editable": False,
        "active": True,
        "sold": 2,
    })
    if created:
        product.photo = SimpleUploadedFile(
            name="product_photo.jpeg", content_type="image/jpeg",
            content=open(path.join(image_dir, "photo_4.jpeg"), "rb").read())
        product.save()

        models.Offer.objects.get_or_create(vendor=vendors[1], product=product, defaults={
            "unit_price": Decimal("200.00"),
            "unit_measure": "g",
            "unit_quantity": 300,
            "shipping_price": Decimal("50.00"),
            "active": True,
            "sold": 1,
        })
        models.Offer.objects.get_or_create(vendor=vendors[2], product=product, defaults={
            "unit_price": Decimal("230.00"),
            "unit_quantity": 2,
            "shipping_price": Decimal("0.00"),
            "active": True,
            "sold": 2,
            "note": "Prodáváme jen po párech, protože sovy jsou společenská zvířata"
        })
    else:
        models.Offer.objects.filter(name=product.name, sold=1).update(product=product, vendor=vendors[1])
        models.Offer.objects.filter(name=product.name, sold=2).update(product=product, vendor=vendors[2])
    products.append(product)

    # create Votes for Products and Vendors
    product_ct = ContentType.objects.get_for_model(models.Product)
    for product in products:
        voters = random.sample(users, random.randint(0, len(users)))
        for voter in voters:
            Vote.objects.get_or_create(content_type=product_ct, object_id=product.pk,
                                       key="user", score=random.random() * 5, user=voter)
        Score.objects.get_or_create(content_type=product_ct, object_id=product.pk,
                                    key="user")[0].recalculate()

    # return new object (as load_test requires)
    return {'users': users, 'vendors': vendors, 'products': products}

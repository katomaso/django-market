Jak testovat
############

:author: katomaso
:date: 2016-04-17

Testy jsou rozdělené do modulů podle náročnosti a pokrytí

- unit
- view
- model

Testy lze spustit přes Makefile jako ::

    make <typ>_test
    # konkretne
    make unit_test
    make test_unit  # funguje take

Makefile vola v pozadi ::

    python manage.py test tests.<typ> --settings=tests.<typ>.settings
    # lze vice specifikovat
    python manage.py test tests.unit.test_users.test_whatever --settings=tests.unit.settings


Emaily
------

Emaily se při nastaveném backendu ::

    # settings.py
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

ukládají do ``django.core.mail.outbox``, což je ``list`` instancí
``django.core.mail.message.EmailMultiAlternatives``. Pozor na drobnosti:

 - *.body*, *.from_email* i *.subject* jsou ``str``
 - *.to* i *.reply_to* jsou ``list[str]``
 - *.recipients* a *.message* jsou instance django tříd

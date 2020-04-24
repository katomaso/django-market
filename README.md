# django-market

Application for a virtual marketplace. Open source, free and too complicated to
be fully tested until there is a real-world usage. My own project failed because
of lack of time. But this project is not-that-badly done so I decided to make it
public. If you have intention of using it then contact me directly.


Want to try out running your own student textbook bazaar? Local food marketplace?
Hobby comunity auctions? Peer-to-peer rental service? You can right now.

## Running

`django-market` is a library that you will include in your django project. You
should be using venv.
```
python -m venv venv
. venv/bin/activate
pip install django django-market
```

The market is spread over a few sub-apps that add extra functionality such as
billing for usage, promo coupons etc. Feel free to include or omit any app you
desire from you INSTALLED_APPS

* `market.core` - cannot be omitted because it is the core
* `market.checkout` - functions to accept payments and select shipping
* `market.search` - embedded fulltext search relaying on postgres' fulltext
* `market.tariff` - if you want the vendors to pay you for their shops

All apps are independent and you can replace with your own implementations. The
sub-apps API is url's names that are included in templates. If you provide endpoints
with the same URL names then you can swap applications freely.


## TL;DR Architecture overview

There are three roles

**Customer**

* can list and buy stuff
* comments on items
* comments on vendors

**Manager**

* setups tariffs for usage for vendors
* bills vendors for usage

**Vendor**

* adds products and/or their own price offer to products
* manages orders from customers
* prints invoices for customers



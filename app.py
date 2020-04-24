#!/usr/bin/env python

import os
import sys
import django.core.wsgi

os.environ['DJANGO_SETTINGS_MODULE'] = 'market.settings'
application = django.core.wsgi.get_wsgi_application()

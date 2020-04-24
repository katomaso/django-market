from tests.settings import *

from market.settings import INSTALLED_APPS as PUBSHOP_APPS

INSTALLED_APPS = PUBSHOP_APPS + ['tests']

if 'market.search' in INSTALLED_APPS:
    # market.search requires postgresql database
    INSTALLED_APPS.remove('market.search')

DEBUG = True

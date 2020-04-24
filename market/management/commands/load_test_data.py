# coding: utf-8
from django.conf import settings

from django.core.management.base import BaseCommand
from importlib import import_module


class Command(BaseCommand):
    """Load testing data and move necessary files via calling <appname>.test_data.load()."""

    help = __doc__
    module_name = "test_data"
    data_pool = None

    def handle(self, *args, **options):
        latest = 'checkout'
        bb = settings.DEBUG
        settings.DEBUG = False
        self._load_test_data(latest)
        settings.DEBUG = bb

    def _load_test_data(self, name):
        try:
            if not name.startswith("market"):
                name = ".".join(("market", name, self.module_name))
            test_data = import_module(name)
            test_data.load()
        except ImportError as e:
            print("Problem importing {0} - {1!s}".format(name, e))

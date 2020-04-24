from __future__ import absolute_import

from .load_testdata import Command as BaseCommand


class Command(BaseCommand):
    help = 'Loads testing data and move necessary (usually media) files via calling <appname>.test_data_extra.load(data_pool)'
    module_name = "test_data_extra"

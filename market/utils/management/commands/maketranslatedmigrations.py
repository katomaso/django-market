#coding: utf-8

from django.core.management.base import BaseCommand
from django.core.management.commands.makemigrations import Command as MakeMigrations


class Command(MakeMigrations):
    leave_locale_alone = True
    can_import_settings = True

    def handle(self, *app_labels, **options):
        super(Command, self).handle(*app_labels, **options)

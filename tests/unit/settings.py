from tests.settings import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': path.join(SITE_ROOT, "db", "test.db"),
    }
}


INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'tests',
    # no other apps - we are unit test :)
]


class DisableMigrations(object):
    """Disable migrations in django >= 1.7."""

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return "notmigrations"


MIGRATION_MODULES = DisableMigrations()

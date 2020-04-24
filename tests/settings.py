from os import path
from market.basic_settings import *

ENABLE_POSTGIS = False  # tests does not play well with postgis

# make django.core.mail.outbox available
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# speedup the test using faster password hasher
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

DATABASES = {
    'default': {
        # Engines: 'sqlite3', 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': path.join(SITE_ROOT, "db", "test.db"),
    }
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null', ],
        },
        'py.warnings': {
            'handlers': ['console', ],
        },
        'django.db': {
            'handlers': ['console', ],
            'level': 'ERROR',
            'propagate': False,
        },
        'factory.generate': {
            'handlers': ['null', ],
        },
        '': {
            'handlers': ['console', ],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
}

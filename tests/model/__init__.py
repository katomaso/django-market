"""
This test bunch uses WebTest for checing if the views are working.

Quick overview of :class django_webtest.WebTest: class is given bellow.

WebTest contains `self.app` which is a wrapper around WSGI requests. It introduces optional
`user` argument (into `app.get` and `app.post`) which takes (string) username or User instance.

Response in this case contains: `templates`, `context`.

CSRF can be diabled via class attr csrf_checks = False
"""


class MockApp:
    """Mock app behaviour from migrations."""

    def __init__(self, models):
        """Prepare model source in form {('pkg.name', 'ModelName'): ModelClass, ...}."""
        self._models = models

    def get_model(self, pkg, model):
        """Function used inmigrations."""
        return self._models[(pkg, model)]

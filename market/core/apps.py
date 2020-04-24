from django.apps import AppConfig


class Market(AppConfig):
    """Market application default settings."""

    name = "market"  # full python path to this module
    label = "market"  # custom label (will be used in models cache)
    verbose_name = "Market application"

    def ready(self):
        pass

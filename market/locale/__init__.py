"""Dispatch requests for data based on settings.LANG_CODE."""
import importlib


def get_data(variable):
    """Get locale-correct variable from data module."""
    from django.conf import settings
    data = importlib.import_module("market.locale." + settings.LANGUAGE_CODE + ".data")
    return getattr(data, variable)

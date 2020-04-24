# -*- coding: utf-8 -*-
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES
from django.forms import BaseForm, ModelChoiceField, CharField
from django.forms.utils import ErrorDict


class EmptyForm(BaseForm):
    """Always (in)valid form based on constructor settings."""

    def __init__(self, *args, **kwargs):
        self.cleaned_data = list()
        self.valid = kwargs.pop("valid", True)
        self._errors = ErrorDict()

    def save(self):
        """Fake save method."""
        return None

    def is_valid(self):
        """Return (in)validity as setup by constructor."""
        return self.valid


class ModelChoiceCreationField(ModelChoiceField):

    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        try:
            return super(ModelChoiceCreationField, self).to_python(value)
        except ValidationError:
            return self.queryset.model.objects.create(**{self.to_field_name or 'pk': value})

    def prepare_value(self, value):
        if self.to_field_name and isinstance(value, int):
            value = self.queryset.model.objects.get(pk=value)
        return super(ModelChoiceCreationField, self).prepare_value(value)


class Model2CharField(CharField):
    """Field that renders model instance as str().

    It doesn't reconstruct the instance from str. That should be handled by forms
    clean_<field> method.
    """

    def __init__(self, klass, *args, **kwargs):
        """Backup model's class."""
        self._klass = klass
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        """Construct str and obtain instance from DB if ID is given."""
        if isinstance(value, self._klass):
            instance = value
        elif value is not None:
            instance = self._klass.objects.get(pk=value)
        else:
            return ""
        return str(instance)

# coding: utf-8
"""Provide generally usable special widgets."""

from django.forms.widgets import Input, TextInput, NumberInput, ClearableFileInput
from django.utils.html import format_html, conditional_escape
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string

from market.core.templatetags.core_tags import as_media


class ClearableImageInput(ClearableFileInput):
    """Redefine clearable template."""

    template_with_initial = (
        '<img src="%(media_url)s" class="clearable-image-field" data-checkbox="%(clear_checkbox_id)s"/>'
        '%(clear_template)s<br /><label>%(input_text)s</label> %(input)s'
    )

    template_with_clear = '<span style="display:none">%(clear)s</span>'

    def __init__(self, template=None, attrs=None):
        self.template = template
        super(ClearableImageInput, self).__init__(attrs)

    def get_template_substitution_values(self, value):
        """Return value-related substitutions."""
        return {
            'media_url': conditional_escape(
                as_media(value.thumbnail if hasattr(value, "thumbnail") else value)
            )
        }

    def render(self, name, value, attrs=None):
        """Render image with thumbnail."""
        if self.template is not None:
            return render_to_string(self.template, context=dict(name=name, value=value, **attrs))
        return super(ClearableImageInput, self).render(name, value, attrs)


class AppendInput(Input):
    """Specialized widget for twitter's Bootstrap with append ability."""

    appended_text = "$"

    def render(self, name, value, attrs=None):
        """Add bootstrap's append ability."""
        append = self.attrs.pop("append", self.appended_text)
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self._format_value(value))
        return format_html('<div class="inputs"><input {}/><span>{}</span></div>',
                           " ".join("{}={}".format(*attr) for attr in final_attrs.items()),
                           append)


class AppendTextInput(TextInput, AppendInput):
    pass


class AppendNumberInput(NumberInput, AppendInput):
    pass


class CurrencyInput(AppendNumberInput):

    appended_text = _("$")


class CurrencyWithoutVATInput(AppendNumberInput):

    appended_text = _("$ without VAT")

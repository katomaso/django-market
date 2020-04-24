from django import template
from django.template.loader import render_to_string


register = template.Library()


@register.simple_tag
def field(formfield, **kwargs):
    """Render a form field with controlable classes and info.

    Possible arguments to this form field
      - `initial` default value for the field
      - `show_info` {bool} controls visibility of "info box"
      TODO
    """
    widget_class = kwargs.pop('widget_class', '').replace(",", " ").split()
    widget_class.append(formfield.field.widget.__class__.__name__)
    formfield.field.widget.attrs.update({"class": " ".join(widget_class)})
    formfield.field.initial = formfield.field.initial or kwargs.pop("initial", None)

    context = dict(
        field=formfield,
        col_class=kwargs.pop('col_class', '').replace(",", " "),
        field_class=kwargs.pop('field_class', '').replace(",", " "),
        label_class=kwargs.pop('label_class', '').replace(",", " "),
        show_info=kwargs.pop('show_info', True),
        show_label=kwargs.pop('show_label', True),
        show_error=kwargs.pop('show_label', True),
        inline=kwargs.pop('inline', False),
        label_size=kwargs.pop("label_size", None),
        col_size=kwargs.pop("col_size", None),
        label_size_small=kwargs.pop("label_size_small", None),
        col_size_small=kwargs.pop("col_size_small", None),
        append=kwargs.pop("append", "")
    )

    if formfield.help_text and "placeholder" not in kwargs:
        kwargs["placeholder"] = formfield.help_text
        formfield.help_text = ''

    formfield.field.widget.attrs.update(kwargs)

    template = (
        'utils/fields/%s.html' % formfield.field.widget.__class__.__name__,
        'utils/fields/field.html',
    )
    return render_to_string(template, context)


@register.simple_tag
def hfield(formfield, **kwargs):
    """Render a form field with additional control over label sizing."""
    label_size = int(kwargs.pop("label_size", 3))
    col_size = kwargs.pop("col_size", 12 - label_size)
    label_size_small = int(12 * (label_size / (col_size + label_size)))
    col_size_small = int(12 * (col_size / (col_size + label_size)))
    kwargs.update({
        "label_size": label_size,
        "col_size": col_size,
        "label_size_small": label_size_small,
        "col_size_small": col_size_small,
    })
    return field(formfield, **kwargs)


@register.simple_tag
def ifield(formfield, **kwargs):
    """Render a form field inline without label and wrapping elements."""
    kwargs["show_label"] = False
    kwargs["inline"] = True
    return field(formfield, **kwargs)

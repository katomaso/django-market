#coding: utf-8
import re
import logging

from django.conf import settings
from django.template import Context, RequestContext
from django.template.loader import get_template
from django.template.exceptions import TemplateDoesNotExist


logger = logging.getLogger(__name__)


def render_template(name, args={}, request=None):
    """Search for templates in all language mutations."""
    lang = settings.LANGUAGE_CODE
    a, b = name.rsplit(".", 2)
    templates = [
        "{0}-{1}.{2}".format(a, lang, b),
        name,
    ]
    if request is not None:
        args.update(request=request)

    for template in templates:
        try:
            obj = get_template(template)
            if not obj:
                continue
            return obj.render(args)
        except TemplateDoesNotExist:
            pass

    raise ValueError("template {0} does not exist even in lang mutations".format(name))


def template_name(mname, cname, ending=".html"):
    """
    >>> template_name("market.core.views", "ProfileEdit")
    market/core/profile-edit.html
    """
    parts = mname.split(".")
    try:
        parts.remove("views")
    except ValueError:
        pass
    if len(parts) >= 2:
        mname = "/".join(parts)
    else:
        mname = ""

    cname = re.sub("[A-Z]", lambda m: "-" + m.group(0).lower(), cname)
    cname = cname.lower().strip("-")
    return "/".join((mname, cname)) + ending


def truncate(text, length):
    text = unicode(text)
    if len(text) < length:
        return text
    if length < 3:
        raise ValueError("Length cannot be smaller than 3")
    first_space = text.find(u" ", length - 3)
    if first_space == -1:
        return text
    return text[:first_space] + u"..."

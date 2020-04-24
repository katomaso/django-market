# coding: utf-8
import logging
import re
import urllib

from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import JsonResponse
from django.views import generic
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import QuerySet
from rest_framework.parsers import JSONParser

from market.core import menu
from market.core import models
from market.utils.templates import template_name

logger = logging.getLogger("market.core")


class FormatterMixin(generic.View):
    """Decide response format on many different criteria.

    In order to follow HATEOAS (and good programming practice) we generate all
    links appearing in the result inside ``get_context_links``.

    html: compose template name from module and view names and render it to the response
    json: return json dump of context in the response

    Notes - here is META['CONTENT_TYPE'] for different types of request

    POST: 'application/x-www-form-urlencoded; charset=UTF-8',

    """
    formats = ("html", "json")
    respond_by = None

    def __init__(self, *args, **kwargs):
        """Set the ``template_name`` for current class to use TemplateView's code.

        The template name is generated as 'module/view/class' so for example class
        in 'market.core.public.UserList' have template 'core/public/user-list.html'
        """
        if not self.template_name:
            self.template_name = template_name(self.__module__, self.__class__.__name__)
        super().__init__(*args, **kwargs)

    def render_json(self):
        """Query for response format."""
        if self.data.get("format") is not None:
            return "json" in self.data["format"]

        return self.is_ajax()

    def is_html(self):
        """Check whether the response will be rendered by us as HTML."""
        return not self.is_ajax()

    def is_ajax(self):
        """Check whether the response should be in AJAX."""
        if self.request.is_ajax():
            return True

        http_accept = self.request.META.get("HTTP_ACCEPT", "")
        if "json" in http_accept or "javascript" in http_accept:
            return True
        return False

    def reverse(self, name, *args, **kwargs):
        """Reverse using current format."""
        kwargs.setdefault("format", "json" if self.is_ajax() else "html")
        return reverse(name, args=args, kwargs=kwargs)

    def get_context_links(self, **kwargs):
        """Gather links to make them accessible in '_links' (JSON HATEOAS) or 'links' HTML.

        This function is called by the get_context_data at the end and all variables are accessible.
        """
        if not hasattr(self.__class__, "has_context_links"):
            logger.info(self.__class__.__name__ + " has no 'get_context_links'")
            return {}
        links = super().get_context_links(**kwargs)
        if "public" not in links:
            links["public"] = {str(item): item.path()
                                     for item in menu.public}
        if "private" not in links:
            links["private"] = {str(item): item.path()
                                     for item in menu.private}
        return links

    def get_context_data(self, **kwargs):
        """Add information about current class to context as well."""
        context = super(FormatterMixin, self).get_context_data(**kwargs)
        upper_case = re.compile("([A-Z])")
        if self.is_html():
            # Add class information only into HTML context
            cname = self.__module__ + self.__class__.__name__
            context.update({
                "classes": upper_case.sub(r'.\1', cname).lower().strip(".").split("."),
            })
        # the last thing is to gather links based on the current context
        links = self.get_context_links(**context)
        # if user made the effort to generate links merge it back
        for link_keyword in ('links', '_links'):
            if link_keyword in context:
                if not isinstance(context[link_keyword], dict):
                    raise ValueError(link_keyword + " in context must be a dictionary")
                logger.info("Updating context links with {} in {}".format(
                    link_keyword, self.__class__.__name__))
                links.update(context.pop(link_keyword))
        if self.is_ajax():
            # JSON HATEOAS requires _links keyword
            context['_links'] = links
        else:
            # (notably) HTML templating cannot take variables starting with _
            context['links'] = links
        return context

    def render_to_response(self, context, **response_kwargs):
        """Serialize `context` into JSON HttpReponse."""
        if self.render_json():
            serializable = {}
            for key, item in context.items():
                if isinstance(item, (str, int, float, bytes, list, tuple, dict)):
                    serializable[key] = item
                if hasattr(item, "serializer"):
                    serializable[key] = item.serializer(item).data
                if key == 'object_list' and hasattr(item.model, "serializer"):
                    serializable[key] = item.model.serializer(item, many=True).data
                if isinstance(item, QuerySet) and hasattr(item.model, "serializer"):
                    serializable[key] = item.model.serializer(item, many=True).data
            return JsonResponse(serializable, safe=False)
        try:
            return super().render_to_response(context, **response_kwargs)
        except:
            return render(self.request, self.template_name, context=context,
                          content_type=None, status=None, using=None)

    def dispatch(self, request, *args, **kwargs):
        """Setup data attribute from parsed BODY first then POST then GET."""
        self.data = {}
        self.data.update(kwargs)
        self.data.update(request.GET)
        self.data.update(request.POST)
        if request.body:
            if "application/x-www-form-urlencoded" in request.META['CONTENT_TYPE']:
                # data are URL-serialized inside request body
                for key, value in urllib.parse.parse_qsl(request.read()):
                    self.data[key.decode('utf-8')] = value
            if "application/json" in request.META['CONTENT_TYPE']:
                self.data.update(JSONParser().parse(request))
        return super().dispatch(request, *args, **kwargs)


class NavigationMixin:
    """Each View should inherit this mixin to provide functional Navigation."""

    @property
    def current_class(self):
        """Extract the name of this class."""
        return template_name(self.__module__, self.__class__.__name__, ending='').replace('/', '-')

    def get_context_data(self, **kwargs):
        """Set context variable 'view' to be used in templates."""
        context = super(NavigationMixin, self).get_context_data(**kwargs)
        context.update({'view': self.current_class})
        return context


class VendorRequiredMixin(LoginRequiredMixin):
    """View requires user to own a vendor."""
    vendor = None

    def dispatch(self, request, *args, **kwargs):
        """Check existence of vendor and redirect to vendor opening page if necessary."""
        try:
            self.vendor = models.Vendor.objects.get(user=request.user, active=True)
        except models.Vendor.DoesNotExist:
            return redirect('admin-vendor')
        return super(VendorRequiredMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add `vendor` into context."""
        context = super(VendorRequiredMixin, self).get_context_data(**kwargs)
        context.update(vendor=self.vendor)
        return context


class CategorizedMixin(FormatterMixin):
    """Resolve category object from slug and add it into instance."""

    def dispatch(self, request, *args, **kwargs):
        """Add self.category before further processing kicks in."""
        self.category = None
        category = self.kwargs.get('category') or self.data.get('category') or ''
        category = category.strip("/") if category else None

        if category:
            self.category = get_object_or_404(models.Category, path=category)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add category into context."""
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class MarketView(FormatterMixin, NavigationMixin, generic.TemplateView):
    """Always adds `is_vendor` and `user` into context."""

    def get_context_data(self, **kwargs):
        """Add `is_vendor` and `user` into context."""
        context = super(MarketView, self).get_context_data(**kwargs)
        if self.request and self.request.user.is_authenticated():
            context.update(is_vendor=models.Vendor.objects.filter(
                user=self.request.user, active=True).exists())
        return context


class MarketListView(MarketView, generic.ListView):
    """Add Formatting and Navigation to ListView.

    Variables appearing in the context:
    -  paginator
    -  page_obj: page holding position attributes ('previous_page_number', 'next_page_number')
    -  is_paginated: None of bool
    -  object_list: already sliced object_list from queryset
    """
    page_kwargs = 'p'

    def get_paginate_by(self, queryset):
        """Get the number of items to paginate or None to prevent pagination in AJAX."""
        return self.request.GET.get("pp", 30) if self.is_html() else None


class MarketDetailView(MarketView, generic.DetailView):
    """Add Formatting and Navigation to DetailView."""

    def get_object(self, queryset):
        """Get object from self.model class using 'slug' or 'pk'."""
        pk = self.kwargs.get(self.pk_url_kwarg)
        slug = self.kwargs.get(self.slug_url_kwarg)
        # Try looking up by pk.
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        if slug is not None and (pk is None or self.query_pk_and_slug):
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        if pk is None and slug is None:
            raise AttributeError("Generic detail view %s must be called with "
                                 "either an object pk or a slug."
                                 % self.__class__.__name__)

        return get_object_or_404(queryset)


class MarketFormView(MarketView, generic.FormView):
    """Let's base FormView on custom template view."""
    pass

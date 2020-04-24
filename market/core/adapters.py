# coding: utf-8
import logging

from django.conf import settings
from django.shortcuts import reverse
from django.utils.translation import ugettext as _

from allauth.account.adapter import DefaultAccountAdapter


dblogger = logging.getLogger("core")


class UserAdapter(DefaultAccountAdapter):
    """Class with aggregated user-related functions."""

    def is_open_for_signup(self, request):
        """Check whether or not the site is open for signups.

        Next to simply returning True/False you can also intervene the
        regular flow by raising an ImmediateHttpResponse
        """
        return not getattr(settings, "TEASER", False)

    def save_user(self, request, user, form, commit=True):
        """Save a new `User` instance using information provided in the form."""
        from allauth.account.utils import user_email, user_field

        data = form.cleaned_data
        name = data.get('name')
        email = data.get('email')
        user_email(user, email)
        user_field(user, 'name', name or '')
        if 'password1' in data:
            user.set_password(data["password1"])
        else:
            user.set_unusable_password()
        self.populate_username(request, user)
        if commit:
            # Ability not to commit makes it easier to derive from
            # this adapter by adding
            user.save()
        return user

    def clean_username(self, username):
        """Validate the username.

        You can hook into this if you want to (dynamically) restrict what
        usernames can be chosen.
        """
        return username

    def clean_email(self, email):
        """Validate an email value.

        You can hook into this if you want to (dynamically) restrict what email
        addresses can be chosen.
        """
        return email

    def get_email_confirmation_redirect_url(self, request):
        """After email confirmation - request logging in."""
        if request.session.get('account_user') is not None:
            if not request.session.get('account_user').has_usable_password():
                return reverse('account_set_password')
        return reverse('account_login')

    # def send_mail(self, template_prefix, email, context):
    #     """Use dbmail backend rather than allauth's."""
    #     dbmail.send_db_mail(template_prefix, recipient=email, context)

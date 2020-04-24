# coding: utf-8
import re
import logging

from django_webtest import WebTest
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.core import mail

from market.core import models
from allauth.account import models as account_models

logger = logging.getLogger(__name__)
re_link = re.compile(r'(https?\://[^\s<>\(\)\'",\|]+)')


class TestUser(WebTest):
    """Basic test of availability of registration."""

    def test_user_creation_and_login(self):
        """Test basic user signup flow.

        - user cannot register with non-matching passwords
        - user cannot register without name
        - user is able to register properly
        - user receives email with confirmation link
        - user is able to confirm their email
        - user is able to log in
        """
        response = self.app.get(reverse('account_signup'))
        form = None
        mail.outbox.clear()

        for f in response.forms.values():
            if "name" in f.fields:
                form = f
                break

        email = "benoit@mandelbrot.com"
        password = "hellomyman"
        # missing name
        form['email'] = email
        # non-matching passwords
        form['password1'] = password
        form['password2'] = "wrong" + password

        form_response = form.submit()
        self.assertLess(form_response.status_code, 300)  # no redirect
        django_form = form_response.context['form']
        self.failUnless(django_form._errors['name'])  # name is mandatory

        # add name
        form['name'] = "Benoit Mandelbrot"
        # still non matching passwords
        form['password1'] = password
        form['password2'] = password[1:]
        form_response = form.submit()
        self.assertLess(form_response.status_code, 300)  # no redirect
        django_form = form_response.context['form']
        self.failUnless(django_form._errors['password2'])  # password mismatch is mandatory

        # submit valid form
        form['password1'] = password
        form['password2'] = password
        response = form.submit()
        self.assertRedirects(response, reverse('account_email_verification_sent'))
        response.follow()

        # test primary email, email creation and confimation email
        self.assertEqual(len(mail.outbox), 1)
        # user should be logged in
        self.assertTrue(response.context['user'].is_authenticated())
        # force logout user
        self.app.reset()
        # test email confirmation
        user = models.User.objects.get(email=email)
        email_address = account_models.EmailAddress.objects.get(user=user)
        self.assertFalse(email_address.verified)

        link = re_link.search(mail.outbox[0].body).group(0).strip(".")
        response = self.app.get(link)
        self.assertRaisesMessage(response,
                                 render_to_response("account/messages/email_confirmed.txt").content)
        # Email confirmation should redirect to login because we don't login automatically
        loginrequest = response.maybe_follow()
        loginform = loginrequest.form
        self.assertTrue(account_models.EmailAddress.objects.get(user=user).verified)

        # try login with invalid credentials
        loginform['login'] = email
        loginform['password'] = "wrong" + password
        response = loginform.submit()

        self.assertGreater(len(response.context['form'].non_field_errors()), 0)
        self.assertFalse(response.context['user'].is_authenticated())

        loginform['login'] = email
        loginform['password'] = password
        response = loginform.submit()

        self.assertTrue(response.context['user'].is_authenticated())
        self.app.reset()

    def test_password_reset(self):
        """Test password reset.

        - user is able to send themselves a reset email
        - user is able to set up new password
        - user is able to login with the new password
        """
        email = "pan@b.cz"
        old_pass, new_pass = "hello", "ahoj"
        user = models.User.objects.get_or_create_verified(
            name="Jan Hus", password=old_pass, email=email)
        webform = self.app.get(reverse('account_reset_password')).form
        webform['email'] = email
        response = webform.submit()
        # confirmation email
        self.assertEqual(len(mail.outbox), 1, response.content.decode('utf-8'))

        link = re_link.search(mail.outbox[0].body).group(0).strip(".")

        response = self.app.get(link)
        response.form['password1'] = new_pass
        response.form['password2'] = new_pass
        response.form.submit()

        user = models.User.objects.get(email=email)  # refresh user
        self.assertTrue(user.check_password(new_pass), link)

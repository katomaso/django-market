"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import mock

from django.test import SimpleTestCase
from market.core.models import User


cursor_wrapper = mock.Mock()
cursor_wrapper.side_effect = RuntimeError("No touching the database!")


@mock.patch("django.db.backends.utils.CursorWrapper", cursor_wrapper)
class UserModelUnitTest(SimpleTestCase):
    def test_get_short_name(self):
        test_user = User()

        test_user.name = "ahoj"
        self.assertEqual(test_user.get_short_name(), "ahoj")

        test_user.name = "Tomas Peterka"
        self.assertEqual(test_user.get_short_name(), "Tomas")

        test_user.name = "Ing. Tomas Peterka"
        self.assertEqual(test_user.get_short_name(), "Tomas")

        test_user.name = "ing. Tomas Peterka"
        self.assertEqual(test_user.get_short_name(), "Tomas")

        test_user.name = "Bc Tomas Almo Peterka PhD."
        self.assertEqual(test_user.get_short_name(), "Tomas")

    def test_name_from_email(self):
        test_user = User()

        test_user.email = "tomas.peterka@seznam.cz"
        test_user.set_name_from_email()
        self.assertEqual(test_user.name, "Tomas Peterka")

        test_user.email = "t.peterka443@seznam.cz"
        test_user.set_name_from_email()
        self.assertEqual(test_user.name, "Peterka")

        test_user.email = "nickname@seznam.cz"
        test_user.set_name_from_email()
        self.assertEqual(test_user.name, "Nickname")

        test_user.email = "mathiew-chomsky#trustless@seznam.cz"
        test_user.set_name_from_email()
        self.assertEqual(test_user.name, "Mathiew Chomsky")

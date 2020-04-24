"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import SimpleTestCase

import mock

cursor_wrapper = mock.Mock()
cursor_wrapper.side_effect = RuntimeError("No touching the database!")


@mock.patch("django.db.backends.utils.CursorWrapper", cursor_wrapper)
class TestDiscountModifiers(SimpleTestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

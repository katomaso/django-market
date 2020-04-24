from django.test import SimpleTestCase

import mock

cursor_wrapper = mock.Mock()
cursor_wrapper.side_effect = RuntimeError("No touching the database!")


@mock.patch("django.db.backends.utils.CursorWrapper", cursor_wrapper)
class SimpleTest(SimpleTestCase):

    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

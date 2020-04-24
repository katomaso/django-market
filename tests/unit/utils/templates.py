import mock
from django.test import TestCase
from market.utils.templates import truncate, template_name


cursor_wrapper = mock.Mock()
cursor_wrapper.side_effect = RuntimeError("No touching the database!")


@mock.patch("django.db.backends.utils.CursorWrapper", cursor_wrapper)
class TruncateTest(TestCase):

    def test_basic(self):
        self.failUnlessEqual(truncate("Ahoj srabe", 5), u"Ahoj...")
        self.failUnlessEqual(truncate("Ahoj srabe", 10), u"Ahoj srabe")
        self.failUnlessEqual(truncate("Ahojasrabe", 4), u"Ahojasrabe")


@mock.patch("django.db.backends.utils.CursorWrapper", cursor_wrapper)
class TemplteNameTest(TestCase):

    def test_basic(self):
        self.failUnlessEqual(template_name('market.users.views', 'ProfileEdit'), "users/profile-edit.html")
        self.failUnlessEqual(template_name('market.users.views', 'Register'), "users/register.html")
        self.failUnlessEqual(template_name('market.core.maps.views', 'ShowMap'), "core/maps/show-map.html")
        self.failUnlessEqual(template_name('market.views', 'Index'), "index.html")

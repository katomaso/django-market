"""Register menu items and more.

This solution takes advantage of python's only-one import system so we know the
instance will be singleton.

 * usermenu takes a function which has one argument an `User` instance and returns
   array of dictionaries with keys "title", "path", ["icon", "class"]
   They are showed in user menu on top-right side of page. It will be shown
   only when a user is logged in

 * adminmenu takes generator which argument is `User` instance. The generator is
   expected to return a dictionary with keys "title", "path", "viewname" ["icon", "class"]
   It will be shown only when a user is logged in

 * navmenu is used in top bar (as toggle buttons). The viewname should be a
   regular expression which matches name of view classes

"""
from django.urls import reverse


class MenuItem:
    """Gets called at every request to see if it should be rendered/emphasized.

    MenuItems are gathered in a singleton list.
    """

    title = None
    url_name = None
    url_kwargs = None

    def is_active(self, request):
        """Return true if current item should be included in the menu."""
        raise NotImplementedError("")

    def is_selected(self, viewname):
        """Return true if current item is selected."""
        raise NotImplementedError("")

    def path(self, **kwargs):
        """Reverse given url_name."""
        return reverse(self.url_name, kwargs=self.url_kwargs)

    def __str__(self):
        return str(self.title)


class Menu:
    """Hold menu items."""

    class Iterator:
        """Iterator sorting based on logical order and real translated title."""

        def __init__(self, data, request=None):
            """Sort keys so iterator can simply loop."""
            self.data = data
            self.request = request
            items = self.data
            self.ordered_keys = sorted(
                items.keys(),
                key=lambda k: (items[k]['order'], str(items[k].get('item'))),
                reverse=False)
            self.ordered_iterator = iter(self.ordered_keys)

        def __iter__(self):
            self.ordered_iterator = iter(self.ordered_keys)
            return self

        def __next__(self):
            item = self.data[next(self.ordered_iterator)]['item']
            while not item.is_active(self.request):
                item = self.data[next(self.ordered_iterator)]['item']
            return item

    def __init__(self):
        """Init data-holding collection."""
        self.items = {}

    def add_item(self, key, menu_item, first=False, last=False):
        """Add MenuItem under correct keys with optional logical order."""
        item = self.items.setdefault(key, {'order': 0})
        if first or last:
            item['order'] = -1 if first else 1
        item['item'] = menu_item

    def iterator(self, request=None):
        """Request-aware iterator."""
        return Menu.Iterator(self.items, request)

    def __iter__(self):
        return self.iterator()


public = Menu()
private = Menu()

class FormTester:
    """Mixin that adds form testing utilities."""

    def leave_one_out(self, form, data, form_key):
        """Take required fields one by one and try to skip them."""
        for omit in data:
            for key, value in data.items():
                if key == omit:
                    continue
            response = form.submit()
            self.assertFalse()


def fill_form(form, data, leave_out=None):
    """Fill the ``form`` with ``data`` optionaly ``leave_out`` one key."""
    for key, value in data.items():
        if key == leave_out:
            continue
        form[key] = value
    return form

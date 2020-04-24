"""Test views using WebTest(Plus).

Quick overview of :class django_webtest.WebTest: class is given bellow.

WebTest contains `self.app` which is a wrapper around WSGI requests.
It introduces optional `user` argument (into `app.get` and `app.post`) which
takes (string) username or User instance.

(Pdb) dir(response)
['__call__', '__class__', '__contains__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__unicode__', '__weakref__', '_abs_headerlist', '_app_iter', '_app_iter__del', '_app_iter__get', '_app_iter__set', '_body__get', '_body__set', '_body_file__del', '_body_file__get', '_body_file__set', '_cache_control__del', '_cache_control__get', '_cache_control__set', '_cache_control_obj', '_cache_expires', '_charset', '_charset__del', '_charset__get', '_charset__set', '_content_type__del', '_content_type__get', '_content_type__set', '_content_type_params__del', '_content_type_params__get', '_content_type_params__set', '_etag_raw', '_find_element', '_follow', '_forms_indexed', '_has_body__get', '_headerlist', '_headerlist__del', '_headerlist__get', '_headerlist__set', '_headers', '_headers__get', '_headers__set', '_json_body__del', '_json_body__get', '_json_body__set', '_make_location_absolute', '_normal_body_regex', '_parse_forms', '_safe_methods', '_status', '_status__get', '_status__set', '_status_code__get', '_status_code__set', '_tag_re', '_text__del', '_text__get', '_text__set', '_unicode_normal_body_regex', '_update_cache_control', '_use_unicode', 'accept_ranges', 'age', 'allow', 'app', 'app_iter', 'app_iter_range', 'body', 'body_file', 'cache_control', 'cache_expires', 'charset', 'click', 'clickbutton', 'client', 'conditional_response', 'conditional_response_app', 'content', 'content_disposition', 'content_encoding', 'content_language', 'content_length', 'content_location', 'content_md5', 'content_range', 'content_type', 'content_type_params', 'context', 'copy', 'date', 'decode_content', 'default_body_encoding', 'default_charset', 'default_conditional_response', 'default_content_type', 'delete_cookie', 'encode_content', 'environ', 'errors', 'etag', 'etag_strong', 'expires', 'follow', 'form', 'forms', 'from_file', 'goto', 'has_body', 'headerlist', 'headers', 'html', 'json', 'json_body', 'modified', 'location', 'lxml', 'maybe_follow', 'md5_etag', 'merge_cookies', 'mustcontain', 'normal_body', 'parser_features', 'pragma', 'pyquery', 'request', 'retry_after', 'server', 'set_cookie', 'showbrowser', 'status', 'status_code', 'status_int', 'streaming', 'template', 'templates', 'test_app', 'testbody', 'text', 'ubody', 'unicode_body', 'unicode_errors', 'unicode_normal_body', 'unset_cookie', 'url', 'vary', 'write', 'www_authenticate', 'xml']
(Pdb) type(response)
<class 'django_webtest.response.DjangoWebtestResponse'>

class DisabledCSRFChecks(WebTest):
    csrf_checks = False


Quick cheat sheet:
response.status_code == 200
response.form || response.forms['id']
form.submit() || form.submit('submit', index=0)
"""

# from django_webtest import WebTest
# from test_plus import TestCase


# class WebTestCase(WebTest, TestCase):
#     """Composed class from two ingenious tests."""
#     pass

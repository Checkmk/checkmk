# encoding: utf-8
from werkzeug.test import create_environ

from cmk.gui import htmllib
from cmk.gui.globals import html, request, RequestContext, AppContext
from cmk.gui.http import Request, Response
from cmk.update_config import DummyApplication


def test_del_vars():
    environ = dict(create_environ(),
                   REQUEST_URI='',
                   QUERY_STRING='foo=foo&_username=foo&_password=bar&bar=bar')
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(Request(environ), Response(is_secure=False))):
        # First we hit the cached property so we can see that the underlying Request object
        # actually got replaced later.
        _ = request.args
        _ = html.request.args

        html.request.set_var("foo", "123")

        html.del_var_from_env("_username")
        html.del_var_from_env("_password")

        # Make test independent of dict sorting
        assert html.request.query_string in ['foo=foo&bar=bar', 'bar=bar&foo=foo']

        assert '_password' not in html.request.args
        assert '_username' not in html.request.args

        # Check the request local proxied version too.
        # Make test independent of dict sorting
        assert request.query_string in ['foo=foo&bar=bar', 'bar=bar&foo=foo']
        assert '_password' not in request.args
        assert '_username' not in request.args

        assert html.request.var("foo") == "123"

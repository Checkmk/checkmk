import pytest
import _pytest
from werkzeug.test import create_environ

import cmk.gui.config as config
import cmk.gui.htmllib as htmllib
from cmk.gui.http import Request, Response
from cmk.gui.globals import html, current_app

monkeypatch = _pytest.monkeypatch.MonkeyPatch()
monkeypatch.setattr(config, "omd_site", lambda: "NO_SITE")


# TODO: Better make our application available?
class DummyApplication(object):
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response
        self.g = {}


@pytest.fixture()
def register_builtin_html():
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    environ = dict(create_environ(), REQUEST_URI='')
    current_app.set_current(DummyApplication(environ, None))
    html.set_current(htmllib.html(Request(environ), Response(is_secure=False)))
    yield
    html.finalize()
    html.unset_current()

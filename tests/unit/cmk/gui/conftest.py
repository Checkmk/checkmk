import pytest
import _pytest
from werkzeug.test import create_environ

import cmk.gui.config as config
import cmk.gui.htmllib as htmllib
from cmk.gui.http import Request, Response
from cmk.gui.globals import html

monkeypatch = _pytest.monkeypatch.MonkeyPatch()
monkeypatch.setattr(config, "omd_site", lambda: "NO_SITE")


@pytest.fixture()
def register_builtin_html():
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    environ = dict(create_environ(), REQUEST_URI='')
    html.set_current(htmllib.html(Request(environ), Response(is_secure=False)))

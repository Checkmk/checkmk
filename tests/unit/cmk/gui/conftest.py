import pytest
import _pytest
import werkzeug.wrappers

import cmk.gui.config as config
import cmk.gui.htmllib as htmllib
import cmk.gui.http as http
from cmk.gui.globals import html

monkeypatch = _pytest.monkeypatch.MonkeyPatch()
monkeypatch.setattr(config, "omd_site", lambda: "NO_SITE")


@pytest.fixture()
def register_builtin_html():
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    wsgi_environ = {
        # TODO: This is no complete WSGI environment. Produce some
        "wsgi.input": "",
        "SCRIPT_NAME": "",
        "REQUEST_URI": "",
    }
    request = http.Request(wsgi_environ)
    response = werkzeug.wrappers.Response()

    html.set_current(htmllib.html(request, response))

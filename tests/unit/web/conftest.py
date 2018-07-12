import __builtin__
import sys
import pytest
import _pytest

import testlib

import cmk

monkeypatch = _pytest.monkeypatch.MonkeyPatch()

import cmk.gui.config as config
import cmk.gui.htmllib as htmllib
import cmk.gui.http as http

monkeypatch.setattr(config, "omd_site", lambda: "NO_SITE")

@pytest.fixture()
def register_builtin_html():
    """This fixture registers a htmllib.html() instance under __builtin__.html
    just like the regular GUI"""
    wsgi_environ = {
        # TODO: This is no complete WSGI environment. Produce some
        "wsgi.input"  : "",
        "SCRIPT_NAME" : "",
    }
    _request = http.Request(wsgi_environ)
    _response = http.Response(_request)

    __builtin__.html = htmllib.html(_request, _response)

#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator

import pytest

import cmk.gui.wsgi.applications.checkmk as checkmk_app
from cmk.gui.http import Response
from cmk.gui.pages import page_registry, PageContext, PageEndpoint, PageHandler
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK

OS_ERROR_PAGE = "test_oserror_page"
OS_ERROR_WSGI_PAGE = "test_oserror_wsgi_page"


def _oserror_wsgi_handler(ctx: PageContext) -> None:
    raise OSError("Apache/mod_wsgi request data read error: Input is already in error state.")


def _oserror_handler(ctx: PageContext) -> None:
    raise OSError("Random OS Error")


@pytest.fixture(name="oserror_pages")
def _oserror_pages() -> Iterator[None]:
    page_registry.register(PageEndpoint(OS_ERROR_PAGE, _oserror_handler))
    page_registry.register(PageEndpoint(OS_ERROR_WSGI_PAGE, _oserror_wsgi_handler))
    try:
        yield
    finally:
        page_registry.unregister(OS_ERROR_PAGE)
        page_registry.unregister(OS_ERROR_WSGI_PAGE)


def test_oserror_wsgi_from_page_handler_returns_400(
    wsgi_app: WebTestAppForCMK,
    monkeypatch: pytest.MonkeyPatch,
    oserror_pages: None,
) -> None:
    """Touching request.values in a broken request body state raises OSError.

    In production the OSError originates from Werkzeug's lazy form parsing, not
    from the page handler itself.  Simulating a genuinely broken wsgi.input
    stream through Flask's test client is not feasible, so we raise the OSError
    directly from the handler as a pragmatic approximation.
    """

    # We can't use the noauth: registration path because _noauth() has a broad
    # "except Exception" that would swallow the OSError before it reaches
    # _process_request's except chain — which is what we're testing here.
    def _no_auth(handler: PageHandler) -> Callable[[PageContext], Response]:
        """Bypass authentication for this test."""
        return handler  # type: ignore[return-value]

    monkeypatch.setattr(checkmk_app, "ensure_authentication", _no_auth)

    resp = wsgi_app.get(f"/NO_SITE/check_mk/{OS_ERROR_WSGI_PAGE}.py", status=400)
    assert resp.status_code == 400


def test_non_wsgi_oserror_from_page_handler_propagates(
    wsgi_app: WebTestAppForCMK,
    monkeypatch: pytest.MonkeyPatch,
    oserror_pages: None,
) -> None:
    """Non-mod_wsgi OSErrors must not be swallowed as 400.

    Only OSErrors that originate from mod_wsgi's broken request stream should
    be caught and turned into a 400.  Any other OSError (e.g. a filesystem
    PermissionError from a page handler) must propagate so it reaches the
    generic exception handler and produces a crash report / 500.
    """

    def _no_auth(handler: PageHandler) -> Callable[[PageContext], Response]:
        return handler  # type: ignore[return-value]

    monkeypatch.setattr(checkmk_app, "ensure_authentication", _no_auth)

    with pytest.raises(OSError, match="Random OS Error"):
        wsgi_app.get(f"/NO_SITE/check_mk/{OS_ERROR_PAGE}.py")

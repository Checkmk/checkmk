#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

from collections.abc import Callable, Iterator

import pytest

import cmk.gui.wsgi.applications.checkmk as checkmk_app
from cmk.gui.exceptions import MKAuthException, MKNotFound, MKUserError, RequestTimeout
from cmk.gui.htmllib.html import html
from cmk.gui.http import (
    ContentDispositionType,
    LEGACY_CONTENT_SECURITY_POLICY,
    Response,
    response,
    STRICT_CONTENT_SECURITY_POLICY,
)
from cmk.gui.pages import page_registry, PageContext, PageEndpoint, PageHandler
from cmk.web.utils.html import HTML
from tests.testlib.gui.web_test_app import WebTestAppForCMK

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


@pytest.mark.usefixtures("oserror_pages")
def test_oserror_wsgi_from_page_handler_returns_400(
    wsgi_app: WebTestAppForCMK, monkeypatch: pytest.MonkeyPatch
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


@pytest.mark.usefixtures("oserror_pages")
def test_non_wsgi_oserror_from_page_handler_propagates(
    wsgi_app: WebTestAppForCMK, monkeypatch: pytest.MonkeyPatch
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


CSP_PAGE = "test_csp_page"
CSP_STRICT_PAGE = "test_csp_strict_page"


def _csp_page(ctx: PageContext) -> None:
    html.write_html(HTML.without_escaping("<div>hello</div>"))


def _csp_strict_page(ctx: PageContext) -> None:
    response.set_content_security_policy(STRICT_CONTENT_SECURITY_POLICY)
    html.write_html(HTML.without_escaping("<div>hello</div>"))


@pytest.fixture(name="csp_pages")
def _csp_pages() -> Iterator[None]:
    page_registry.register(PageEndpoint(CSP_PAGE, _csp_page))
    page_registry.register(PageEndpoint(CSP_STRICT_PAGE, _csp_strict_page))
    try:
        yield
    finally:
        page_registry.unregister(CSP_PAGE)
        page_registry.unregister(CSP_STRICT_PAGE)


@pytest.mark.usefixtures("csp_pages")
def test_csp_default_legacy_policy_is_applied(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    """A page that sets no policy gets the legacy CSP from the central hook."""
    resp = logged_in_wsgi_app.get(f"/NO_SITE/check_mk/{CSP_PAGE}.py", status=200)
    assert resp.headers["Content-Security-Policy"] == LEGACY_CONTENT_SECURITY_POLICY.serialize()


@pytest.mark.usefixtures("csp_pages")
def test_csp_page_can_opt_into_strict_policy(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    """A page that opts into the strict policy keeps it; the hook does not overwrite it."""
    resp = logged_in_wsgi_app.get(f"/NO_SITE/check_mk/{CSP_STRICT_PAGE}.py", status=200)
    assert resp.headers["Content-Security-Policy"] == STRICT_CONTENT_SECURITY_POLICY.serialize()


REQUEST_TIMEOUT_PAGE = "test_request_timeout_page"


def _request_timeout_page(ctx: PageContext) -> None:
    raise RequestTimeout("Your request timed out after 110 seconds.")


@pytest.fixture(name="request_timeout_page")
def _request_timeout_page_fixture() -> Iterator[None]:
    page_registry.register(PageEndpoint(REQUEST_TIMEOUT_PAGE, _request_timeout_page))
    try:
        yield
    finally:
        page_registry.unregister(REQUEST_TIMEOUT_PAGE)


def test_request_timeout_returns_503(
    logged_in_wsgi_app: WebTestAppForCMK, request_timeout_page: None
) -> None:
    """A RequestTimeout (e.g. during a CSV export) must surface as 503.

    Callers scripting against output formats like csv_export rely on the
    status code alone to detect failure, since the response body still has
    content-type 200-OK shaped output either way.
    """
    resp = logged_in_wsgi_app.get(
        f"/NO_SITE/check_mk/{REQUEST_TIMEOUT_PAGE}.py?output_format=csv_export", status=503
    )
    assert resp.status_code == 503


def test_request_timeout_plain_error_returns_503(
    logged_in_wsgi_app: WebTestAppForCMK, request_timeout_page: None
) -> None:
    resp = logged_in_wsgi_app.get(
        f"/NO_SITE/check_mk/{REQUEST_TIMEOUT_PAGE}.py?_plain_error=1", status=503
    )
    assert resp.status_code == 503


def test_request_timeout_ajax_returns_503(
    logged_in_wsgi_app: WebTestAppForCMK, request_timeout_page: None
) -> None:
    resp = logged_in_wsgi_app.get(
        f"/NO_SITE/check_mk/{REQUEST_TIMEOUT_PAGE}.py?_ajaxid=1", status=503
    )
    assert resp.status_code == 503


CSV_EXPORT_TIMEOUT_PAGE = "test_csv_export_timeout_page"


def _csv_export_timeout_page(ctx: PageContext) -> None:
    """Mimics a CSV exporter: set export headers, write partial output, then time out."""
    response.set_content_type("text/csv")
    response.set_content_disposition(ContentDispositionType.ATTACHMENT, "export.csv")
    html.write_text_permissive("partial,csv,row\n")
    raise RequestTimeout("Your request timed out after 110 seconds.")


@pytest.fixture(name="csv_export_timeout_page")
def _csv_export_timeout_page_fixture() -> Iterator[None]:
    page_registry.register(PageEndpoint(CSV_EXPORT_TIMEOUT_PAGE, _csv_export_timeout_page))
    try:
        yield
    finally:
        page_registry.unregister(CSV_EXPORT_TIMEOUT_PAGE)


def test_request_timeout_during_csv_export_resets_response(
    logged_in_wsgi_app: WebTestAppForCMK, csv_export_timeout_page: None
) -> None:
    """A timeout mid-export must not leave the exporter's headers/body in place.

    Otherwise the client gets a non-2xx status alongside a Content-Disposition:
    attachment header and a body mixing leftover CSV bytes with the error message --
    neither a valid CSV nor a page a browser can render, and (per review on the
    original fix) a stale attachment header on an error status made browsers show
    their own opaque native error screen instead of the actual message.
    """
    resp = logged_in_wsgi_app.get(
        f"/NO_SITE/check_mk/{CSV_EXPORT_TIMEOUT_PAGE}.py?output_format=csv_export", status=503
    )
    assert resp.status_code == 503
    assert resp.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "Content-Disposition" not in resp.headers
    assert b"partial,csv,row" not in resp.body
    assert b"Your request timed out" in resp.body


MK_USER_ERROR_PAGE = "test_mk_user_error_page"
MK_AUTH_EXCEPTION_PAGE = "test_mk_auth_exception_page"
MK_NOT_FOUND_PAGE = "test_mk_not_found_page"


def _mk_user_error_page(ctx: PageContext) -> None:
    raise MKUserError("some_field", "Invalid value")


def _mk_auth_exception_page(ctx: PageContext) -> None:
    raise MKAuthException("Permission denied")


def _mk_not_found_page(ctx: PageContext) -> None:
    raise MKNotFound("Not found")


@pytest.fixture(name="error_status_pages")
def _error_status_pages_fixture() -> Iterator[None]:
    page_registry.register(PageEndpoint(MK_USER_ERROR_PAGE, _mk_user_error_page))
    page_registry.register(PageEndpoint(MK_AUTH_EXCEPTION_PAGE, _mk_auth_exception_page))
    page_registry.register(PageEndpoint(MK_NOT_FOUND_PAGE, _mk_not_found_page))
    try:
        yield
    finally:
        page_registry.unregister(MK_USER_ERROR_PAGE)
        page_registry.unregister(MK_AUTH_EXCEPTION_PAGE)
        page_registry.unregister(MK_NOT_FOUND_PAGE)


@pytest.mark.parametrize(
    "page_name,expected_status",
    [
        (MK_USER_ERROR_PAGE, 400),
        (MK_AUTH_EXCEPTION_PAGE, 401),
        (MK_NOT_FOUND_PAGE, 404),
    ],
)
def test_mkhttpexception_status_propagates_in_plain_render_branch(
    logged_in_wsgi_app: WebTestAppForCMK,
    error_status_pages: None,
    page_name: str,
    expected_status: int,
) -> None:
    """Any MKHTTPException must carry its real status through the plain render branch.

    _render_exception() used to compute the status from MKHTTPException.status but never
    apply it in the non-ajax/non-_plain_error branch, so every such error -- not just
    RequestTimeout -- silently came back as 200. Using output_format=csv_export (rather
    than the default "html") exercises the exact same status-applying line while avoiding
    make_header()'s frontend asset loading, which this test environment doesn't provide.
    """
    resp = logged_in_wsgi_app.get(
        f"/NO_SITE/check_mk/{page_name}.py?output_format=csv_export", status=expected_status
    )
    assert resp.status_code == expected_status

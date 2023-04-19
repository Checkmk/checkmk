#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import functools
import http.client as http_client
import traceback
from collections.abc import Callable
from typing import TYPE_CHECKING

import flask

import livestatus

import cmk.utils.paths
import cmk.utils.profile
import cmk.utils.store
from cmk.utils.exceptions import MKException

from cmk.gui import http, pages, sites
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.exceptions import (
    FinalizeRequest,
    HTTPRedirect,
    MKAuthException,
    MKConfigError,
    MKNotFound,
    MKUnauthenticatedException,
    MKUserError,
)
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response, Response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.utils.urls import requested_file_name
from cmk.gui.wsgi.applications.utils import (
    AbstractWSGIApp,
    ensure_authentication,
    fail_silently,
    handle_unhandled_exception,
    plain_error,
)
from cmk.gui.wsgi.type_defs import WSGIResponse

if TYPE_CHECKING:
    # TODO: Directly import from wsgiref.types in Python 3.11, without any import guard
    from _typeshed.wsgi import StartResponse, WSGIEnvironment

# TODO
#  * derive all exceptions from werkzeug's http exceptions.


def _noauth(func: pages.PageHandlerFunc) -> Callable[[], Response]:
    #
    # We don't have to set up anything because we assume this is only used for special calls. We
    # however have to make sure all errors get written out in plaintext, without HTML.
    #
    # Currently these are:
    #  * noauth:run_cron
    #  * noauth:deploy_agent
    #  * noauth:ajax_graph_images
    #  * noauth:automation
    #
    @functools.wraps(func)
    def _call_noauth():
        try:
            func()
        except HTTPRedirect:
            raise
        except Exception as e:
            html.write_text(str(e))
            if active_config.debug:
                html.write_text(traceback.format_exc())

        return response

    return _call_noauth


def _page_not_found() -> Response:
    # TODO: This is a page handler. It should not be located in generic application
    # object. Move it to another place
    if request.has_var("_plain_error"):
        html.write_text(_("Page not found"))
    else:
        title = _("Page not found")
        make_header(
            html,
            title,
            Breadcrumb(
                [
                    BreadcrumbItem(
                        title="Nowhere",
                        url=None,
                    ),
                    BreadcrumbItem(
                        title=title,
                        url="javascript:document.location.reload(false)",
                    ),
                ]
            ),
        )
        html.show_error(_("This page was not found. Sorry."))
    html.footer()

    response.status_code = http_client.NOT_FOUND
    return response


def _render_exception(e: Exception, title: str) -> Response:
    if plain_error():
        return Response(
            response=[
                "{}{}\n".format(("%s: " % title) if title else "", e),
            ],
            mimetype="text/plain",
        )

    if not fail_silently():
        make_header(html, title, Breadcrumb())
        html.show_error(str(e))
        html.footer()

    return response


def default_response_headers(req: http.Request) -> dict[str, str]:
    headers = {
        # Disable caching for all our pages as they are mostly dynamically generated,
        # user related and are required to be up-to-date on every refresh
        "Cache-Control": "no-cache",
    }
    return headers


_OUTPUT_FORMAT_MIME_TYPES = {
    "json": "application/json",
    "json_export": "application/json",
    "jsonp": "application/javascript",
    "csv": "text/csv",
    "csv_export": "text/csv",
    "python": "text/plain",
    "text": "text/plain",
    "html": "text/html",
    "xml": "text/xml",
    "pdf": "application/pdf",
    "x-tgz": "application/x-tgz",
}


def get_output_format(output_format: str) -> str:
    if output_format not in _OUTPUT_FORMAT_MIME_TYPES:
        return "html"
    return output_format


def get_mime_type_from_output_format(output_format: str) -> str:
    return _OUTPUT_FORMAT_MIME_TYPES[output_format]


class CheckmkApp(AbstractWSGIApp):
    """The Checkmk GUI WSGI entry point"""

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        """Is called by the WSGI server to serve the current page"""
        with cmk.utils.store.cleanup_locks(), sites.cleanup_connections():
            return _process_request(environ, start_response, debug=self.debug)


def _process_request(  # pylint: disable=too-many-branches
    environ: WSGIEnvironment,
    start_response: StartResponse,
    debug: bool = False,
) -> WSGIResponse:
    resp: Response
    try:
        file_name = requested_file_name(request, on_error="raise")

        if file_name is None:
            page_handler = _page_not_found
        elif _handler := pages.get_page_handler(file_name):
            page_handler = ensure_authentication(_handler)
        elif _handler := pages.get_page_handler(f"noauth:{file_name}"):
            page_handler = _noauth(_handler)
        else:
            page_handler = _page_not_found

        resp = page_handler()

    except MKNotFound:
        resp = _page_not_found()

    except HTTPRedirect as exc:
        return flask.redirect(exc.url)(environ, start_response)

    except FinalizeRequest as exc:
        # TODO: Remove all FinalizeRequest exceptions from all pages and replace it with a `return`.
        #       It may be necessary to rewire the control-flow a bit as this exception could have
        #       been used to short-circuit some code and jump directly to the response. This
        #       needs to be changed as well.
        resp = response
        resp.status_code = exc.status

    except livestatus.MKLivestatusNotFoundError as e:
        resp = _render_exception(e, title=_("Data not found"))

    except MKUserError as e:
        resp = _render_exception(e, title=_("Invalid user input"))

    except MKUnauthenticatedException as e:
        resp = _render_exception(e, title=_("Not authenticated"))

    except MKAuthException as e:
        resp = _render_exception(e, title=_("Permission denied"))

    except livestatus.MKLivestatusException as e:
        resp = _render_exception(e, title=_("Livestatus problem"))
        resp.status_code = http_client.BAD_GATEWAY

    except MKConfigError as e:
        resp = _render_exception(e, title=_("Configuration error"))
        logger.error("MKConfigError: %s", e)

    except MKException as e:
        resp = _render_exception(e, title=_("General error"))
        logger.error("%s: %s", e.__class__.__name__, e)

    except Exception:
        resp = handle_unhandled_exception()
        if debug:
            raise

    return resp(environ, start_response)

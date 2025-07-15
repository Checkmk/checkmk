#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import functools
import http.client as http_client
import traceback
from collections.abc import Callable
from wsgiref.types import StartResponse, WSGIEnvironment

import flask
from werkzeug.exceptions import RequestEntityTooLarge

import livestatus

import cmk.ccc.store
from cmk.ccc.exceptions import MKException

import cmk.utils.paths

from cmk.gui import pages, sites
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config, Config
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
from cmk.gui.http import request, Response, response
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

from cmk import trace
from cmk.crypto import MKCryptoException

tracer = trace.get_tracer()

# TODO
#  * derive all exceptions from werkzeug's http exceptions.


def _noauth(handler: pages.PageHandlerFunc | type[pages.Page]) -> Callable[[Config], Response]:
    #
    # We don't have to set up anything because we assume this is only used for special calls. We
    # however have to make sure all errors get written out in plaintext, without HTML.
    #
    # Currently these are:
    #  * noauth:deploy_agent
    #  * noauth:automation
    #
    @functools.wraps(handler)
    def _call_noauth(config: Config) -> Response:
        try:
            if isinstance(handler, type):
                handler().handle_page(config)
            else:
                handler(config)
        except HTTPRedirect:
            raise
        except Exception as e:
            html.write_text_permissive(str(e))
            if config.debug:
                html.write_text_permissive(traceback.format_exc())

        return response

    return _call_noauth


def _page_not_found(config: Config) -> Response:
    # TODO: This is a page handler. It should not be located in generic application
    # object. Move it to another place
    if request.has_var("_plain_error"):
        html.write_text_permissive(_("Page not found"))
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
        html.open_ts_container(
            container="div",
            function_name="insert_before",
            arguments={"targetElementId": "main_page_content"},
        )
        html.show_error(str(e))
        html.close_div()
        html.footer()

    return response


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

    __slots__ = ("testing",)

    def __init__(self, debug: bool = False, testing: bool = False) -> None:
        super().__init__(debug)
        self.testing = testing

    @tracer.instrument("CheckmkApp.wsgi_app")
    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        """Is called by the WSGI server to serve the current page"""
        with cmk.ccc.store.cleanup_locks(), sites.cleanup_connections():
            # The configuration is currently loaded in the FileBasedSession.open_session() method,
            # because we need the configuration for the session management. Need to figure out
            # whether we can directly hand it over to get rid of the proxy object.
            # Flask.__call__()
            #     Flask.wsgi_app()
            #         self.request_context()
            #         RequestContext.push()
            #             FileBasedSession.open_session(app, request)
            #     	        config.initialize()
            #         Flask.full_dispatch_request()
            #             Flask.finalize_request()
            #                 Flask.make_response()
            #                     AbstractWSGIApp.__call__()
            #                         CheckmkApp.wsgi_app()
            config = active_config
            return _process_request(
                config, environ, start_response, debug=self.debug, testing=self.testing
            )


def _process_request(
    config: Config,
    environ: WSGIEnvironment,
    start_response: StartResponse,
    debug: bool = False,
    testing: bool = False,
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

        resp = page_handler(config)

    except MKNotFound:
        resp = _page_not_found(config)

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

    except (MKException, MKCryptoException) as e:
        resp = _render_exception(e, title=_("General error"))
        logger.error("%s: %s", e.__class__.__name__, e)

    except RequestEntityTooLarge as e:
        resp = _render_exception(e, title=_("Request too large"))

    except Exception:
        if debug or testing:
            raise
        resp = handle_unhandled_exception()

    resp.set_caching_headers()
    return resp(environ, start_response)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import functools
import http.client as http_client
import json
import traceback
from typing import Callable, Dict, TYPE_CHECKING

import livestatus

import cmk.utils.paths
import cmk.utils.profile
import cmk.utils.store

from cmk.gui import config as config_module
from cmk.gui import htmllib, http, pages, sites
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.context import AppContext, RequestContext
from cmk.gui.ctx_stack import app_stack, request_stack
from cmk.gui.display_options import DisplayOptions
from cmk.gui.exceptions import (
    FinalizeRequest,
    HTTPRedirect,
    MKAuthException,
    MKConfigError,
    MKGeneralException,
    MKUnauthenticatedException,
    MKUserError,
)
from cmk.gui.globals import html, PrependURLFilter, request, response
from cmk.gui.http import Response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.utils.json import patch_json
from cmk.gui.utils.output_funnel import OutputFunnel
from cmk.gui.utils.theme import Theme
from cmk.gui.utils.timeout_manager import TimeoutManager
from cmk.gui.utils.transaction_manager import TransactionManager
from cmk.gui.utils.urls import requested_file_name
from cmk.gui.wsgi.applications.utils import (
    ensure_authentication,
    fail_silently,
    handle_unhandled_exception,
    plain_error,
)

if TYPE_CHECKING:
    from cmk.gui.wsgi.type_defs import StartResponse, WSGIEnvironment, WSGIResponse

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
        except Exception as e:
            html.write_text(str(e))
            if active_config.debug:
                html.write_text(traceback.format_exc())

        return response

    return _call_noauth


def get_and_wrap_page(script_name: str) -> Callable[[], Response]:
    """Get the page handler and wrap authentication logic when needed.

    For all "noauth" page handlers the wrapping part is skipped. In the `ensure_authentication`
    wrapper everything needed to make a logged-in request is listed.
    """
    _handler = pages.get_page_handler(script_name)
    if _handler is None:
        # Some pages do skip authentication. This is done by adding
        # noauth: to the page handler, e.g. "noauth:run_cron" : ...
        # TODO: Eliminate those "noauth:" pages. Eventually replace it by call using
        #       the now existing default automation user.
        _handler = pages.get_page_handler("noauth:" + script_name)
        if _handler is not None:
            return _noauth(_handler)

    if _handler is None:
        return _page_not_found

    return ensure_authentication(_handler)


def _page_not_found() -> Response:
    # TODO: This is a page handler. It should not be located in generic application
    # object. Move it to another place
    if request.has_var("_plain_error"):
        html.write_text(_("Page not found"))
    else:
        title = _("Page not found")
        html.header(
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

    return response


def _render_exception(e: Exception, title: str) -> Response:
    if plain_error():
        return Response(
            response=[
                "%s%s\n" % (("%s: " % title) if title else "", e),
            ],
            mimetype="text/plain",
        )

    if not fail_silently():
        html.header(title, Breadcrumb())
        html.show_error(str(e))
        html.footer()

    return response


def default_response_headers(req: http.Request) -> Dict[str, str]:
    headers = {
        # Disable caching for all our pages as they are mostly dynamically generated,
        # user related and are required to be up-to-date on every refresh
        "Cache-Control": "no-cache",
    }

    # Would be better to put this to page individual code, but we currently have
    # no mechanism for a page to set do this before the authentication is made.
    if requested_file_name(req) == "webapi":
        headers["Access-Control-Allow-Origin"] = "*"

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


class CheckmkApp:
    """The Check_MK GUI WSGI entry point"""

    def __init__(self, debug=False):
        self.debug = debug

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        req = http.Request(environ)

        output_format = get_output_format(
            req.get_ascii_input_mandatory("output_format", "html").lower()
        )
        mime_type = get_mime_type_from_output_format(output_format)

        resp = Response(headers=default_response_headers(req), mimetype=mime_type)
        funnel = OutputFunnel(resp)

        timeout_manager = TimeoutManager()
        timeout_manager.enable_timeout(req.request_timeout)

        theme = Theme()
        config_obj = config_module.make_config_object(config_module.get_default_config())

        nobody = LoggedInNobody()
        with AppContext(self, stack=app_stack()), RequestContext(
            req=req,
            resp=resp,
            funnel=funnel,
            config_obj=config_obj,
            user=nobody,
            transactions=TransactionManager(req, nobody),
            html_obj=htmllib.html(req, resp, funnel, output_format),
            timeout_manager=timeout_manager,
            display_options=DisplayOptions(),
            theme=theme,
            stack=request_stack(),
            url_filter=PrependURLFilter(),
        ), patch_json(json):
            config_module.initialize()
            theme.from_config(active_config.ui_theme)
            return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        """Is called by the WSGI server to serve the current page"""
        with cmk.utils.store.cleanup_locks(), sites.cleanup_connections():
            return _process_request(environ, start_response, debug=self.debug)


def _process_request(
    environ: WSGIEnvironment,
    start_response: StartResponse,
    debug: bool = False,
) -> WSGIResponse:  # pylint: disable=too-many-branches
    resp: Response
    try:
        page_handler = get_and_wrap_page(requested_file_name(request))
        resp = page_handler()
    except HTTPRedirect as e:
        # This can't be a new Response as it can have already cookies set/deleted by the pages.
        # We can't return the response because the Exception has been raised instead.
        # TODO: Remove all HTTPRedirect exceptions from all pages. Making the Exception a subclass
        #       of Response may also work as it can then be directly returned from here.
        resp = response
        resp.status_code = e.status
        resp.headers["Location"] = e.url

    except FinalizeRequest as e:
        # TODO: Remove all FinalizeRequest exceptions from all pages and replace it with a `return`.
        #       It may be necessary to rewire the control-flow a bit as this exception could have
        #       been used to short-circuit some code and jump directly to the response. This
        #       needs to be changed as well.
        resp = response
        resp.status_code = e.status

    except livestatus.MKLivestatusNotFoundError as e:
        resp = _render_exception(e, title=_("Data not found"))

    except MKUserError as e:
        resp = _render_exception(e, title=_("Invalid user input"))

    except MKAuthException as e:
        resp = _render_exception(e, title=_("Permission denied"))

    except livestatus.MKLivestatusException as e:
        resp = _render_exception(e, title=_("Livestatus problem"))
        resp.status_code = http_client.BAD_GATEWAY

    except MKUnauthenticatedException as e:
        resp = _render_exception(e, title=_("Not authenticated"))
        resp.status_code = http_client.UNAUTHORIZED

    except MKConfigError as e:
        resp = _render_exception(e, title=_("Configuration error"))
        logger.error("MKConfigError: %s", e)

    except (MKGeneralException, cmk.utils.store.MKConfigLockTimeout) as e:
        resp = _render_exception(e, title=_("General error"))
        logger.error("%s: %s", e.__class__.__name__, e)

    except Exception:
        resp = handle_unhandled_exception()
        if debug:
            raise

    return resp(environ, start_response)

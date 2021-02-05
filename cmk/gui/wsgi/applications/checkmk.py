#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable
import functools
import http.client as http_client
import traceback

import livestatus

import cmk.utils.paths
import cmk.utils.profile
import cmk.utils.store

from cmk.gui import config, pages, http, htmllib
from cmk.gui.display_options import DisplayOptions
from cmk.gui.exceptions import (
    MKUserError,
    MKConfigError,
    MKGeneralException,
    MKAuthException,
    MKUnauthenticatedException,
    FinalizeRequest,
    HTTPRedirect,
)
from cmk.gui.globals import html, RequestContext, AppContext
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.http import Response
from cmk.gui.wsgi.applications.utils import (
    ensure_authentication,
    fail_silently,
    handle_unhandled_exception,
    load_all_plugins,
    plain_error,
)

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
            if config.debug:
                html.write_text(traceback.format_exc())

        return html.response

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
    if html.request.has_var("_plain_error"):
        html.write(_("Page not found"))
    else:
        title = _("Page not found")
        html.header(
            title,
            Breadcrumb([
                BreadcrumbItem(
                    title="Nowhere",
                    url=None,
                ),
                BreadcrumbItem(
                    title=title,
                    url="javascript:document.location.reload(false)",
                ),
            ]))
        html.show_error(_("This page was not found. Sorry."))
    html.footer()

    return html.response


def _render_exception(e: Exception, title: str = "") -> Response:
    if title:
        title = "%s: " % title

    if plain_error():
        html.set_output_format("text")
        html.write("%s%s\n" % (title, e))

    elif not fail_silently():
        html.header(title, Breadcrumb())
        html.show_error(str(e))
        html.footer()

    return html.response


class CheckmkApp:
    """The Check_MK GUI WSGI entry point"""
    def __init__(self, debug=False):
        self.debug = debug

    def __call__(self, environ, start_response):
        req = http.Request(environ)
        with AppContext(self), RequestContext(
                req=req,
                html_obj=htmllib.html(req),
                display_options=DisplayOptions(),
        ):
            config.initialize()
            html.init_modes()
            return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        """Is called by the WSGI server to serve the current page"""
        with cmk.utils.store.cleanup_locks():
            return _process_request(environ, start_response, debug=self.debug)


def _process_request(environ, start_response, debug=False) -> Response:  # pylint: disable=too-many-branches
    try:
        html.init_modes()

        # Make sure all plugins are available as early as possible. At least
        # we need the plugins (i.e. the permissions declared in these) at the
        # time before the first login for generating auth.php.
        load_all_plugins()

        page_handler = get_and_wrap_page(html.myfile)
        response = page_handler()
    except HTTPRedirect as e:
        # This can't be a new Response as it can have already cookies set/deleted by the pages.
        # We can't return the response because the Exception has been raised instead.
        # TODO: Remove all HTTPRedirect exceptions from all pages. Making the Exception a subclass
        #       of Response may also work as it can then be directly returned from here.
        response = html.response
        response.status_code = e.status
        response.headers["Location"] = e.url

    except FinalizeRequest as e:
        # TODO: Remove all FinalizeRequest exceptions from all pages and replace it with a `return`.
        #       It may be necessary to rewire the control-flow a bit as this exception could have
        #       been used to short-circuit some code and jump directly to the response. This
        #       needs to be changed as well.
        response = html.response
        response.status_code = e.status

    except livestatus.MKLivestatusNotFoundError as e:
        response = _render_exception(e, title=_("Data not found"))

    except MKUserError as e:
        response = _render_exception(e, title=_("Invalid user Input"))

    except MKAuthException as e:
        response = _render_exception(e, title=_("Permission denied"))

    except livestatus.MKLivestatusException as e:
        response = _render_exception(e, title=_("Livestatus problem"))
        response.status_code = http_client.BAD_GATEWAY

    except MKUnauthenticatedException as e:
        response = _render_exception(e, title=_("Not authenticated"))
        response.status_code = http_client.UNAUTHORIZED

    except MKConfigError as e:
        response = _render_exception(e, title=_("Configuration error"))
        logger.error("MKConfigError: %s", e)

    except MKGeneralException as e:
        response = _render_exception(e, title=_("General error"))
        logger.error("MKGeneralException: %s", e)

    except Exception:
        response = handle_unhandled_exception()
        if debug:
            raise

    return response(environ, start_response)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client as http_client
from werkzeug.exceptions import abort, HTTPException

from cmk.gui import config, pages, http, htmllib
from cmk.gui.display_options import DisplayOptions
from cmk.gui.exceptions import MKUnauthenticatedException
from cmk.gui.globals import html, RequestContext, AppContext
from cmk.gui.http import Response
from cmk.gui.wsgi.applications.utils import (
    ensure_authentication,
    handle_unhandled_exception,
)


class CheckmkSetupSearchApp:
    """The WSGI entry point for the app handling the setup search"""
    def __call__(self, environ, start_response) -> Response:
        req = http.Request(environ)
        with AppContext(self), RequestContext(req=req,
                                              display_options=DisplayOptions(),
                                              html_obj=htmllib.html(req)):
            config.initialize()
            return _process_request(environ, start_response)


def _process_request(environ, start_response) -> Response:
    try:
        if html.myfile != "ajax_search_setup":
            abort(
                http_client.NOT_FOUND,
                description=f"CheckmkSetupSearchApp is reserved exclusively for the Setup search "
                f"(ajax_search_setup), but it was called with the page {html.myfile}.",
            )

        page_handler = pages.get_page_handler(html.myfile)
        if not page_handler:
            raise KeyError("The page_handler for ajax_search_setup is missing.")

        page_handler_auth = ensure_authentication(page_handler)
        response = page_handler_auth()

        if '"result_code": 0' not in response.get_data(as_text=True):
            abort(http_client.BAD_REQUEST)

        response.status_code = http_client.OK

    except HTTPException as http_excpt:
        # do not write crash report in this case
        response = html.response
        response.status_code = http_excpt.code or http_client.BAD_REQUEST

    except MKUnauthenticatedException:
        # do not write crash report in this case
        response = html.response
        response.status_code = http_client.UNAUTHORIZED

    except Exception:
        response = handle_unhandled_exception()
        response.status_code = http_client.INTERNAL_SERVER_ERROR

    return response(environ, start_response)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple, TYPE_CHECKING

from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.routing import Map, Rule, Submount

from cmk.gui.wsgi.applications import CheckmkApp, CheckmkRESTAPI
from cmk.gui.wsgi.applications.helper_apps import discover_receiver, dump_environ_app, test_formdata

if TYPE_CHECKING:
    from cmk.gui.wsgi.type_defs import StartResponse, WSGIApplication, WSGIEnvironment, WSGIResponse


WSGI_ENV_ARGS_NAME = "x-checkmk.args"


def create_url_map(debug: bool = False) -> Map:
    """Instantiate all WSGI Apps and put them into the URL-Map."""
    debug_rules = [
        Rule("/dump.py", endpoint="debug-dump"),
        Rule("/form.py", endpoint="debug-form"),
    ]

    return Map(
        [
            Submount(
                "/<string:site>",
                [
                    Submount(
                        "/check_mk",
                        [
                            Rule("/", endpoint="cmk"),
                            *(debug_rules if debug else []),
                            Rule(
                                "/api/<string:version>/domain-types/internal/actions"
                                "/discover-receiver/invoke",
                                endpoint="discover-receiver",
                            ),
                            Rule("/api/<string:version>/<path:path>", endpoint="rest-api"),
                            Rule("/<string:script>", endpoint="cmk"),
                        ],
                    ),
                ],
            )
        ]
    )


def make_router(debug: bool = False) -> WSGIApplication:
    """Route the requests to the correct application.

    This router uses Werkzeug's URL-Map system to dispatch to the correct application. The
    applications are stored as references within the URL-Map and can then be called directly,
    without the necessity of doing import-magic.
    """
    # We create the URL-map once and re-use it on every request.
    url_map = create_url_map(debug=debug)

    # Fix wsgi.url_scheme with werkzeug.middleware.proxy_fix.ProxyFix
    # would be always http instead
    cmk_app = ProxyFix(app=CheckmkApp(debug=debug).__call__)  # type: ignore[arg-type]
    api_app = ProxyFix(app=CheckmkRESTAPI(debug=debug).wsgi_app)  # type: ignore[arg-type]

    endpoints: Dict[str, WSGIApplication] = {
        "cmk": cmk_app,
        "rest-api": api_app,
        "debug-dump": dump_environ_app,
        "debug-form": test_formdata,
        "discover-receiver": discover_receiver,
    }

    def router(environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        urls = url_map.bind_to_environ(environ)
        try:
            result: Tuple[str, Mapping[str, Any]] = urls.match(return_rule=False)
            endpoint_name, args = result  # pylint: disable=unpacking-non-sequence
            endpoint = endpoints[endpoint_name]
        except HTTPException as e:
            # HTTPExceptions are WSGI apps
            endpoint = e
            args = {}

        environ[WSGI_ENV_ARGS_NAME] = args
        return endpoint(environ, start_response)

    return router

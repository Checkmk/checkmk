#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Submount, Rule

from cmk.gui.wsgi.applications import CheckmkApp, CheckmkRESTAPI
from cmk.gui.wsgi.applications.helper_apps import dump_environ_app, test_formdata

WSGI_ENV_ARGS_NAME = 'x-checkmk.args'


def create_url_map(debug=False):
    """Instantiate all WSGI Apps and put them into the URL-Map."""
    debug_rules = [
        Rule("/dump.py", endpoint=dump_environ_app),
        Rule("/form.py", endpoint=test_formdata),
    ]

    cmk_app = CheckmkApp()
    api_app = CheckmkRESTAPI(debug=debug).wsgi_app

    return Map([
        Submount('/<string:site>', [
            Submount("/check_mk", [
                Rule("/", endpoint=cmk_app),
                *(debug_rules if debug else []),
                Rule("/api/<string:version>/<path:path>", endpoint=api_app),
                Rule("/<string:script>", endpoint=cmk_app),
            ]),
        ])
    ])


def make_router(debug=False):
    """Route the requests to the correct application.

    This router uses Werkzeug's URL-Map system to dispatch to the correct application. The
    applications are stored as references within the URL-Map and can then be called directly,
    without the necessity of doing import-magic.
    """
    # We create the URL-map once and re-use it on every request.
    url_map = create_url_map(debug=debug)

    def router(environ, start_response):
        urls = url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
        except HTTPException as e:
            # HTTPExceptions are WSGI apps
            endpoint = e
            args = ()

        if endpoint is None:
            raise Exception(endpoint, args, environ)

        environ[WSGI_ENV_ARGS_NAME] = args
        return endpoint(environ, start_response)

    return router

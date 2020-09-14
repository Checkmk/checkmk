#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Submount, Rule

import cmk.utils.version as cmk_version
from cmk.gui.wsgi.applications import CheckmkApp, CheckmkApiApp, openapi_spec_dir
from cmk.gui.wsgi.applications.helper_apps import dump_environ_app, test_formdata
from cmk.gui.wsgi.middleware import OverrideRequestMethod, with_context_middleware

WSGI_ENV_ARGS_NAME = 'x-checkmk.args'


def create_url_map(debug=False):
    """Instantiate all WSGI Apps and put them into the URL-Map."""
    _api_app = CheckmkApiApp(
        __name__,
        debug=debug,
        specification_dir=openapi_spec_dir(),
    )
    # NOTE
    # The URL will always contain the most up to date major version number, so that clients
    # exploring the API (browsers, etc.) will have a structural stability guarantee. Within major
    # versions only additions of fields or endpoints are allowed, never field changes or removals.
    # If a new major version is created it should be ADDED here and not replace the older version.
    # NOTE: v0 means totally unstable until we hit v1.
    _api_app.add_api_blueprint(
        'checkmk.yaml',
        base_path='/%s/check_mk/api/v0/' % cmk_version.omd_site(),
    )

    wrapped_api_app = with_context_middleware(OverrideRequestMethod(_api_app).wsgi_app)
    cmk_app = CheckmkApp()

    debug_rules = [
        Rule("/dump.py", endpoint=dump_environ_app),
        Rule("/form.py", endpoint=test_formdata),
    ]

    return Map([
        Submount('/<string:site>', [
            Submount("/check_mk", [
                Rule("/", endpoint=cmk_app),
                *(debug_rules if debug else []),
                Submount('/api', [
                    Rule("/", endpoint=wrapped_api_app),
                    Rule("/<path:path>", endpoint=wrapped_api_app),
                ]),
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

        environ[WSGI_ENV_ARGS_NAME] = args
        return endpoint(environ, start_response)

    return router

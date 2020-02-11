#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import threading

from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Submount, Rule

import cmk
from cmk.gui.wsgi.applications import CheckmkApp, CheckmkApiApp, openapi_spec_dir
from cmk.gui.wsgi.applications.helper_apps import dump_environ_app, test_formdata
from cmk.gui.wsgi.middleware import OverrideRequestMethod, with_context_middleware

WSGI_ENV_ARGS_NAME = 'x-checkmk.args'


def create_url_map():
    """Instantiate all WSGI Apps and put them into the URL-Map."""
    _api_app = CheckmkApiApp(
        __name__,
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
        base_path='/%s/check_mk/api/v0/' % cmk.omd_site(),
        validate_responses=True,
    )

    wrapped_api_app = with_context_middleware(OverrideRequestMethod(_api_app).wsgi_app)
    cmk_app = CheckmkApp()

    return Map([
        Submount('/<string:site>', [
            Submount("/check_mk", [
                Rule("/", endpoint=cmk_app),
                Rule("/dump.py", endpoint=dump_environ_app),
                Rule("/form.py", endpoint=test_formdata),
                Submount('/api', [
                    Rule("/", endpoint=wrapped_api_app),
                    Rule("/<path:path>", endpoint=wrapped_api_app),
                ]),
                Rule("/<string:script>", endpoint=cmk_app),
            ]),
        ])
    ])


def router(environ, start_response, _url_map=[]):  # pylint: disable=dangerous-default-value
    """Route the requests to the correct application.

    This router uses Werkzeug's URL-Map system to dispatch to the correct application. The
    applications are stored as references within the URL-Map and can then be called directly,
    without the necessity of doing import-magic.

    We cache the URL-Map after it has been created at the first request. There is currently no
    way to clear this cache, nor should there be a need to do so.
    """
    # We try not to hit a lock on every request, only when we assume it's the first one.
    if not _url_map:
        with threading.Lock():
            # We create the URL-Map as late as possible so that the Apps are not instantiated
            # at import-time where they would try to create their contexts prematurely.
            if not _url_map:
                _url_map.append(create_url_map())

    url_map = _url_map[0]

    urls = url_map.bind_to_environ(environ)
    try:
        endpoint, args = urls.match()
    except HTTPException as e:
        # HTTPExceptions are WSGI apps
        endpoint = e
        args = ()

    environ[WSGI_ENV_ARGS_NAME] = args
    return endpoint(environ, start_response)

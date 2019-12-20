#!/usr/bin/python
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
import contextlib
import threading

from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Submount, Rule

import cmk
from cmk.gui.wsgi.applications import CheckmkApp, CheckmkApiApp, openapi_spec_dir
from cmk.gui.wsgi.applications.helper_apps import dump_environ_app

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

    wrapped_api_app = OverrideRequestMethod(_api_app)
    cmk_app = CheckmkApp()

    return Map([
        Submount('/<string:site>', [
            Submount("/check_mk", [
                Rule("/", endpoint=cmk_app),
                Rule("/dump.py", endpoint=dump_environ_app),
                Submount('/api', [
                    Rule("/", endpoint=wrapped_api_app),
                    Rule("/<path:path>", endpoint=wrapped_api_app),
                ]),
                Rule("/<string:script>", endpoint=cmk_app),
            ]),
        ])
    ])


class OverrideRequestMethod(object):
    """Middleware to allow inflexible clients to override the HTTP request method.

    Common convention is to allow for a X-HTTP-Method-Override HTTP header to be set.

    Please be aware that no validation for a "correct" HTTP verb is being done by this middleware,
    as this should be handled by other layers.
    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        override = environ.get('HTTP_X_HTTP_METHOD_OVERRIDE')
        if override:
            environ['REQUEST_METHOD'] = override
        return self.app(environ, start_response)


def router(raw_environ, start_response, _url_map=[]):  # pylint: disable=dangerous-default-value
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

    with _fixed_checkmk_env(raw_environ) as environ:
        urls = url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
        except HTTPException as e:
            # HTTPExceptions are WSGI apps
            endpoint = e
            args = ()

    raw_environ[WSGI_ENV_ARGS_NAME] = args
    return endpoint(raw_environ, start_response)


@contextlib.contextmanager
def _fixed_checkmk_env(raw_environ):
    # The WSGI spec doesn't require PATH_INFO to be set, yet Werkzeug's routing requires it.
    environ = raw_environ.copy()
    path_info = environ.get('PATH_INFO')
    if not path_info or path_info == '/':
        environ['PATH_INFO'] = environ['SCRIPT_NAME']
    yield environ

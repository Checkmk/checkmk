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

from werkzeug.routing import Map, Submount, Rule

from cmk.gui.wsgi.applications.checkmk import CheckmkApp
from cmk.gui.wsgi.applications.helper_apps import dump_environ_app

WSGI_ENV_ARGS_NAME = 'x-checkmk.args'


def create_url_map():
    app = CheckmkApp()

    return Map([
        Submount('/<string:site>', [
            Submount("/check_mk", [
                Rule("/", endpoint=app),
                Rule("/dump.py", endpoint=dump_environ_app),
                Rule("/<string:script>", endpoint=app),
            ]),
        ])
    ])


def router(raw_environ, start_response, _url_map=[]):  # pylint: disable=dangerous-default-value
    # We create the Environment as late as possible so that we can use it within our tests.
    with threading.Lock():
        if not _url_map:
            _url_map.append(create_url_map())
        url_map = _url_map[0]

    with _fixed_checkmk_env(raw_environ) as environ:
        urls = url_map.bind_to_environ(environ)
        endpoint, args = urls.match()

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

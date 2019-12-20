#!/usr/bin/env python
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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
import functools
import sys
import traceback

import flask
import pathlib2
import werkzeug

from connexion import FlaskApi, AbstractApp, RestyResolver, problem  # type: ignore
from connexion.apps.flask_app import FlaskJSONEncoder  # type: ignore

from cmk.gui import crash_reporting
from cmk.gui.log import logger
from cmk.gui.wsgi.auth import with_user
from cmk.utils import paths


def openapi_spec_dir():
    return paths.web_dir + "/htdocs/openapi"


class CheckmkApi(FlaskApi):
    pass


def wrap_result(function_resolver, result_wrap):
    """Wrap the result of a resolver with another function.

    """
    @functools.wraps(function_resolver)
    def wrapper(*args, **kw):
        return result_wrap(function_resolver(*args, **kw))

    return wrapper


class CheckmkApiApp(AbstractApp):
    def __init__(self, import_name, **kwargs):
        resolver = RestyResolver('cmk.gui.plugins.openapi.endpoints')
        resolver.function_resolver = wrap_result(resolver.function_resolver, with_user)

        kwargs.setdefault('resolver', resolver)
        super(CheckmkApiApp, self).__init__(import_name, api_cls=CheckmkApi, **kwargs)

    def create_app(self):
        """Will be persisted on self.app, where __call__ will dispatch to."""
        app = flask.Flask(self.import_name)
        app.json_encoder = FlaskJSONEncoder
        return app

    def get_root_path(self):
        return pathlib2.Path(self.app.root_path)

    def add_api_blueprint(self, specification, **kwargs):
        api = self.add_api(specification, **kwargs)  # type: CheckmkApi
        api.add_swagger_ui()
        self.app.register_blueprint(api.blueprint)
        return api

    def log_error(self, exception):
        crash = crash_reporting.GUICrashReport.from_exception()
        crash_reporting.CrashReportStore().save(crash)
        logger.exception("Unhandled exception (Crash-ID: %s)", crash.ident_to_text())

        _, exc_val, exc_tb = sys.exc_info()
        if hasattr(exception, 'name'):
            resp = problem(
                title=exception.name,
                detail=exception.description,
                status=exception.code,
            )
        else:
            resp = problem(
                title=repr(exc_val),
                detail=''.join(traceback.format_tb(exc_tb)),
                status=500,
            )
        return FlaskApi.get_response(resp)

    def set_errors_handlers(self):
        for error_code in werkzeug.exceptions.default_exceptions:
            self.app.register_error_handler(error_code, self.log_error)
        self.app.register_error_handler(Exception, self.log_error)

    def run(self, port=None, server=None, debug=None, host=None, **options):
        raise NotImplementedError()

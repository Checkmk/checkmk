#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import urllib.parse
from typing import Dict, Type

from connexion import ProblemException  # type: ignore[import]
from werkzeug.exceptions import HTTPException

from werkzeug.routing import Map, Submount

from cmk.gui import config
from cmk.gui.exceptions import MKUserError, MKAuthException
from cmk.gui.openapi import ENDPOINT_REGISTRY
from cmk.gui.plugins.openapi.utils import problem
from cmk.gui.wsgi.auth import verify_user, bearer_auth
from cmk.gui.wsgi.middleware import with_context_middleware, OverrideRequestMethod
from cmk.gui.wsgi.wrappers import ParameterDict
from cmk.utils import paths, crash_reporting
from cmk.utils.exceptions import MKException

logger = logging.getLogger('cmk.gui.wsgi.rest_api')

EXCEPTION_STATUS: Dict[Type[Exception], int] = {
    MKUserError: 400,
    MKAuthException: 401,
}


def openapi_spec_dir():
    return paths.web_dir + "/htdocs/openapi"


class ServeFile:
    def __init__(self, param):
        self.file = param['file']

    def __call__(self, environ, start_response):
        raise Exception(self.file)


class ServeSpec(ServeFile):
    ...


class CheckmkRESTAPI:
    def __init__(self, debug: bool = False):
        self.debug = debug
        # TODO: Add resources for swagger-ui and json/yaml endpoints.
        # TODO: Add redoc.js endpoint.
        rules = []
        for endpoint in ENDPOINT_REGISTRY:
            if self.debug:
                # This helps us to make sure we can always generate a valid OpenAPI yaml file.
                _ = endpoint.to_operation_dict()

            rules.append(endpoint.werkzeug_rule())
        self.url_map = Map([
            Submount(
                "/<path:_path>",
                [
                    # Rule("/ui/<path:file>", endpoint=ServeFile),
                    # Rule("/doc/<path:file>", endpoint=ServeFile),
                    # Rule("/openapi.yaml", endpoint=ServeSpec),
                    # Rule("/openapi.json", endpoint=ServeSpec),
                    *[endpoint.werkzeug_rule() for endpoint in ENDPOINT_REGISTRY],
                ],
            ),
        ])
        self.wsgi_app = with_context_middleware(OverrideRequestMethod(self._wsgi_app))

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def _wsgi_app(self, environ, start_response):
        urls = self.url_map.bind_to_environ(environ)
        try:
            func, path_args = urls.match()

            # Remove this again (see Submount above), so the validators don't go crazy.
            del path_args['_path']

            auth_header = environ.get('HTTP_AUTHORIZATION', '')
            try:
                rfc7662 = bearer_auth(auth_header)
            except MKException as exc:
                return problem(
                    status=401,
                    title=str(exc),
                    ext={'auth_header': auth_header},
                )(environ, start_response)

            with verify_user(rfc7662['sub'], rfc7662):
                wsgi_app = func(ParameterDict(path_args))
                return wsgi_app(environ, start_response)
        except HTTPException as e:
            # We don't want to log explicit HTTPExceptions as these are intentional.
            # HTTPExceptions are WSGI apps
            return e(environ, start_response)
        except ProblemException as exc:
            # FIXME: Replace connexion exceptions with our own.
            return problem(
                status=exc.status,
                detail=exc.detail,
                title=exc.title,
                type_=exc.type,
                ext=exc.ext,
            )(environ, start_response)
        except MKException as exc:
            if self.debug:
                raise

            return problem(
                status=EXCEPTION_STATUS.get(type(exc), 500),
                title=str(exc),
                detail="An exception occurred.",
            )(environ, start_response)
        except Exception as exc:
            crash = APICrashReport.from_exception()
            crash_reporting.CrashReportStore().save(crash)
            logger.exception("Unhandled exception (Crash-ID: %s)", crash.ident_to_text())
            if self.debug:
                raise

            crash_url = f"/{config.omd_site()}/check_mk/crash.py?" + urllib.parse.urlencode([
                ("crash_id", crash.ident_to_text()),
                ("site", config.omd_site()),
            ],)

            return problem(status=EXCEPTION_STATUS.get(type(exc), 500),
                           title=str(exc),
                           detail="An internal error occured while processing your request.",
                           ext={
                               'crash_report': {
                                   'href': crash_url,
                                   'method': 'get',
                                   'rel': 'cmk/crash-report',
                                   'type': 'text/html',
                               },
                               'crash_id': crash.ident_to_text(),
                           })(environ, start_response)


class APICrashReport(crash_reporting.ABCCrashReport):
    """API specific crash reporting class.
    """
    @classmethod
    def type(cls):
        return "rest_api"

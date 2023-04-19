#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import logging
import pathlib
import typing as t

import werkzeug
from flask import Flask, redirect
from werkzeug.debug import DebuggedApplication
from werkzeug.exceptions import BadRequest
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import safe_join

from cmk.utils import paths

from cmk.gui import http
from cmk.gui.session import FileBasedSession
from cmk.gui.wsgi.blueprints.checkmk import checkmk
from cmk.gui.wsgi.blueprints.rest_api import rest_api
from cmk.gui.wsgi.profiling import ProfileSwitcher

if t.TYPE_CHECKING:
    # Here due to cyclical imports
    Environments = t.Literal["production", "testing", "development"]

logger = logging.getLogger(__name__)


class CheckmkFlaskApp(Flask):
    request_class = http.Request
    response_class = http.Response
    session_interface = FileBasedSession()


def make_wsgi_app(debug: bool = False, testing: bool = False) -> Flask:
    """Create the Checkmk WSGI application.

    Args:
        debug:
            Whether debug mode is enabled. When set, the interactive debugger will be enabled

        testing:
            Enable testing mode. When set, exceptions will be propagated, instead of using Flask's
            error handling machinery.

    Returns:
        The WSGI application
    """

    app = CheckmkFlaskApp(__name__)
    app.debug = debug
    app.testing = testing
    # Config needs a request context to work. :(
    # Until this can work, we need to do it at runtime in `FileBasedSession`.
    # app.config["PERMANENT_SESSION_LIFETIME"] = active_config.user_idle_timeout

    # NOTE: The ordering of the blueprints is important, due to routing precedence, i.e. Rule
    # instances which are evaluated later but have the same URL will be ignored. The first Rule
    # instance will win.
    app.register_blueprint(rest_api)
    app.register_blueprint(checkmk)

    # Some middlewares we want to have available in all environments
    app.wsgi_app = ProxyFix(app.wsgi_app)  # type: ignore[assignment]
    app.wsgi_app = ProfileSwitcher(  # type: ignore[assignment]
        app.wsgi_app,
        profile_file=pathlib.Path(paths.var_dir) / "multisite.profile",
    ).wsgi_app

    if debug:
        app.wsgi_app = DebuggedApplication(  # type: ignore[assignment]
            app.wsgi_app,
            evalex=True,
            pin_logging=False,
            pin_security=False,
        )

    # This URL could still be used in bookmarks of customers.
    # Needs to be here, not in blueprints/rest_api.py as the URL is at a lower level than the API.
    # NOTE: In the packaged product, this is done by the Site-Apache, but here we need to do it
    # in Python so that the development server reflects the behavior of the finished product.
    @app.route("/<string:site>/check_mk/openapi/")
    def redirect_doc(site: str) -> werkzeug.Response:
        dest = safe_join("/", site, "check_mk/api/doc")
        if dest is None:
            raise BadRequest()
        return redirect(dest)

    return app


__all__ = ["make_wsgi_app", "CheckmkFlaskApp"]

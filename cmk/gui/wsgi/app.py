#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import logging
import warnings

import werkzeug
from flask import Flask, redirect
from werkzeug.debug import DebuggedApplication
from werkzeug.exceptions import BadRequest
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import safe_join

from cmk.ccc.version import Edition
from cmk.gui.features import features_registry
from cmk.gui.flask_app import CheckmkFlaskApp
from cmk.gui.session import FileBasedSession
from cmk.gui.wsgi.blueprints.checkmk import checkmk
from cmk.gui.wsgi.blueprints.rest_api import rest_api

from .trace import instrument_app_dependencies

logger = logging.getLogger(__name__)


def make_wsgi_app(edition: Edition, debug: bool = False, testing: bool = False) -> Flask:
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
    try:
        features = features_registry[str(edition)]
    except KeyError:
        raise ValueError(f"Invalid edition: {edition}")

    app = CheckmkFlaskApp(__name__, FileBasedSession(), features)
    app.debug = debug
    app.testing = testing
    # Config needs a request context to work. :(
    # Until this can work, we need to do it at runtime in `FileBasedSession`.
    # app.config["PERMANENT_SESSION_LIFETIME"] = active_config.session_mgmt["user_idle_timeout"]

    instrument_app_dependencies()

    # NOTE: some schemas are generically generated. On default, for duplicate schema names, we
    # get name+increment which we have deemed fine. We can therefore suppress those warnings.
    # https://github.com/marshmallow-code/apispec/issues/444
    warnings.filterwarnings("ignore", message="Multiple schemas resolved to the name")
    warnings.filterwarnings(
        "ignore",
        ".* has already been added to the spec",
        category=UserWarning,
    )

    # NOTE: The ordering of the blueprints is important, due to routing precedence, i.e. Rule
    # instances which are evaluated later but have the same URL will be ignored. The first Rule
    # instance will win.
    app.register_blueprint(rest_api)
    app.register_blueprint(checkmk)

    # Some middlewares we want to have available in all environments
    app.wsgi_app = ProxyFix(app.wsgi_app)  # type: ignore[method-assign]

    if debug:
        app.wsgi_app = DebuggedApplication(  # type: ignore[method-assign]
            app.wsgi_app,
            evalex=not testing,  # sets werkzeug.debug.preserve_context, which changes the flask globals behaviour
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


__all__ = ["make_wsgi_app"]

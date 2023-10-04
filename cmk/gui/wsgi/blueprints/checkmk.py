#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import functools
import typing

import flask
import werkzeug
from flask import Blueprint, current_app, redirect, Response
from flask.blueprints import BlueprintSetupState
from werkzeug.exceptions import BadRequest
from werkzeug.security import safe_join

from cmk.utils import store

from cmk.gui import hooks, main_modules, sites
from cmk.gui.http import request
from cmk.gui.utils.timeout_manager import timeout_manager
from cmk.gui.wsgi.applications import CheckmkApp
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars
from cmk.gui.wsgi.middleware import PatchJsonMiddleware

if typing.TYPE_CHECKING:
    from _typeshed.wsgi import WSGIApplication

ResponseTypes = flask.Response | werkzeug.Response

checkmk = Blueprint(
    "checkmk",
    __name__,
    url_prefix="/<string:site>",
)


# Global variables (through the g object) which we need in every request.
@checkmk.before_app_request
def before_app_request() -> None:
    set_global_vars()


@checkmk.record_once
def first_request(state: BlueprintSetupState) -> None:
    # Will be called once on setup-time.
    main_modules.load_plugins()


@checkmk.before_request
def before_request() -> None:
    if not current_app.debug:
        # We're running in production. In the development server, we can't set any
        # signals, because then "serve_simple" will refuse to run the app.
        timeout_manager.enable_timeout(request.request_timeout)
    hooks.call("request-start")


@checkmk.after_request
def after_request(response: Response) -> Response:
    store.release_all_locks()
    sites.disconnect()
    hooks.call("request-end")
    if not current_app.debug:
        timeout_manager.disable_timeout()

    return response


@checkmk.route("/")
def redirect_checkmk(site: str) -> ResponseTypes:
    destination = safe_join("/", site, "check_mk")
    if destination is not None:
        return redirect(destination)

    raise BadRequest


@checkmk.route("/check_mk")
def check_mk_root(site: str) -> ResponseTypes:
    return redirect(f"/{site}/check_mk/")


@checkmk.route("/<path:path>", methods=["GET", "PUT", "POST", "DELETE"])
def page(site: str, path: str) -> WSGIApplication:
    # TODO: Carve out parts from CheckmkApp and move them into this file.
    # Rationale:
    #   Currently the CheckmkApp itself has an internal "router", which potentially duplicates
    #   the routing functionality of Flask. By moving this portion of the code "one layer up" we
    #   can potentially save on complexity and code size.
    return app_instance(debug=current_app.debug)


@functools.lru_cache
def app_instance(debug: bool) -> WSGIApplication:
    app = CheckmkApp(debug=debug)
    app.wsgi_app = PatchJsonMiddleware(app.wsgi_app).wsgi_app  # type: ignore[method-assign]
    return app


__all__ = ["checkmk"]

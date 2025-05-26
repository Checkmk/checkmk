#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import functools
from wsgiref.types import WSGIApplication

from flask import Blueprint, current_app, make_response, Response, send_from_directory

from cmk.ccc import store
from cmk.ccc.site import get_omd_config

from cmk.utils import paths
from cmk.utils.paths import omd_root

from cmk.gui import hooks, sites
from cmk.gui.wsgi.applications import CheckmkRESTAPI
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars
from cmk.gui.wsgi.middleware import OverrideRequestMethod

rest_api = Blueprint(
    "rest-api",
    __name__,
    url_prefix="/<string:site>/check_mk/api",
)
# Global variables (through the g object) which we need in every request.
rest_api.before_app_request(set_global_vars)


@functools.lru_cache
def app_instance(debug: bool, testing: bool) -> WSGIApplication:
    app = CheckmkRESTAPI(debug=debug, testing=testing)
    return OverrideRequestMethod(app.wsgi_app)


@rest_api.before_request
def before_request() -> None:
    hooks.call("request-start")


@rest_api.after_request
def after_request(response: Response) -> Response:
    store.release_all_locks()
    sites.disconnect()
    hooks.call("request-end")
    return response


@rest_api.route("/<string:version>/<path:path>", methods=["GET", "PUT", "POST", "DELETE"])
def endpoint(site: str, version: str, path: str) -> WSGIApplication:
    # TODO: Carve out parts from `CheckmkRESTAPI` and move them here, decorated by @rest_api.route
    return app_instance(debug=current_app.debug, testing=current_app.testing)


@rest_api.route("/doc/", defaults={"file_name": "index.html"})
@rest_api.route("/doc/<path:file_name>")
def serve_redoc(site: str, file_name: str) -> Response:
    return send_from_directory(paths.web_dir / "htdocs/openapi", file_name)


@functools.lru_cache
def _get_receiver_port() -> int:
    # make sure we really only ever report a number and nothing more
    return int(get_omd_config(omd_root)["CONFIG_AGENT_RECEIVER_PORT"])


@rest_api.route("/<string:version>/domain-types/internal/actions/discover-receiver/invoke")
def discover_receiver(site: str, version: str) -> Response:
    """Report the port of the agent receiver

    We report the agent receivers port on this unprotected URL.
    We don't give away information here that an attacker could not find out with a port scan.
    """
    return make_response(f"{_get_receiver_port()}", 200)


__all__ = ["rest_api"]

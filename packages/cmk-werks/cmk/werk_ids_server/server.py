#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import secrets

from flask import current_app, Flask, jsonify, request, Response
from werkzeug.middleware.proxy_fix import ProxyFix

from cmk.werk_ids_server._db import reserve

# The reserve must stay at 10 usable IDs after `werk new`. `werk new` tops the
# reserve up and then immediately consumes one ID for the werk it creates, so we
# hand out one extra (10 kept + 1 consumed) to keep the steady-state buffer at 10.
_MAX_RESERVABLE_IDS = 11

app = Flask(__name__)
setattr(app, "wsgi_app", ProxyFix(app.wsgi_app, x_for=1))
_logger = logging.getLogger(__name__)


def _error(status_code: int, message: str) -> Response:
    response = jsonify({"error": message})
    response.status_code = status_code
    return response


@app.before_request
def _auth() -> Response | None:
    if request.endpoint == "health":
        return None
    secret = current_app.config["secret_file"].read_text().strip()
    if not secret:
        _logger.error("Empty secret in %(path)r", {"path": str(current_app.config["secret_file"])})
        return _error(500, "Server misconfigured.")
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or not secrets.compare_digest(
        auth.removeprefix("Bearer "), secret
    ):
        return _error(401, "Invalid or missing authorization.")
    return None


@app.get("/")
def health() -> Response:
    return jsonify({"status": "ok"})


@app.get("/v1/connect")
def connect() -> Response:
    return jsonify({"status": "ok"})


@app.post("/v1/reserve")
def reserve_ids() -> Response:
    data = request.get_json(silent=True) or {}
    local_werk_ids_count = data.get("local_werk_ids_count")
    if not isinstance(local_werk_ids_count, int) or local_werk_ids_count < 0:
        return _error(400, "Field 'local_werk_ids_count' must be a non-negative integer.")

    to_be_reserved = _MAX_RESERVABLE_IDS - local_werk_ids_count
    if to_be_reserved <= 0:
        return jsonify({"reserved_werk_ids": []})

    reserved = reserve(current_app.config["db"], to_be_reserved)
    _logger.info(
        "Client IP: %(client_ip)r, reserved IDs: %(reserved)r",
        {"client_ip": request.remote_addr, "reserved": reserved},
    )
    return jsonify({"reserved_werk_ids": reserved})

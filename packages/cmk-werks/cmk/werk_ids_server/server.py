#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import secrets

from flask import abort, current_app, Flask, jsonify, request, Response
from werkzeug.middleware.proxy_fix import ProxyFix

from cmk.werk_ids_server._db import reserve

_MAX_RESERVABLE_IDS = 10

app = Flask(__name__)
setattr(app, "wsgi_app", ProxyFix(app.wsgi_app, x_for=1))
_logger = logging.getLogger(__name__)


@app.before_request
def _auth() -> None:
    if request.endpoint == "health":
        return
    secret = current_app.config["secret_file"].read_text().strip()
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or not secrets.compare_digest(
        auth.removeprefix("Bearer "), secret
    ):
        abort(401)


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
        abort(400)

    to_be_reserved = _MAX_RESERVABLE_IDS - local_werk_ids_count
    if to_be_reserved <= 0:
        return jsonify({"reserved_werk_ids": []})

    reserved = reserve(current_app.config["db"], to_be_reserved)
    _logger.info("Client IP: %r, reserved IDs: %r", request.remote_addr, reserved)
    return jsonify({"reserved_werk_ids": reserved})

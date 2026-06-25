#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Flatten the ``maps_connections`` global setting into ConnectionConfig.

Connections are a native Checkmk global setting (``maps_connections``, a list
edited via a FormSpec in WATO, owned by ConfigDomainMaps). WATO stores each
entry in the nested FormSpec ("form") shape — ``type`` / ``target`` /
``metric_history`` are CascadingSingleChoice tuples and the ``automation_secret``
is a Checkmk password-store reference. The daemon reads the list read-only and
flattens it here to the runtime :class:`ConnectionConfig`, resolving the secret
to plaintext via the password store (``cmk.utils.password_store`` — Flask-free,
the same mechanism the HTTP-proxy config uses).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

from cmk.maps.backend.schemas.connection import ConnectionConfig
from cmk.utils import password_store

logger = logging.getLogger(__name__)


def _resolve_secret(value: object) -> str | None:
    """Resolve a FormSpec ``Password`` value (password-store ref) to plaintext."""
    if value is None:
        return None
    try:
        return password_store.extract_formspec_password(value)  # type: ignore[arg-type]
    except Exception as exc:
        logger.warning(
            "Could not resolve a connection's automation secret: %(exc)s",
            {"exc": exc},
        )
        return None


def _cascade(value: object) -> tuple[str, object] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2 and isinstance(value[0], str):
        return value[0], value[1]
    return None


def connection_form_to_config(entry: Mapping[str, object]) -> ConnectionConfig | None:
    """Flatten one ``maps_connections`` list entry into a ConnectionConfig.

    Returns ``None`` for a malformed entry (logged) so one bad record cannot
    abort loading the rest.
    """
    cid = entry.get("id")
    if not isinstance(cid, str) or not cid:
        return None
    # ``label`` is a required field in the WATO form (like a site's alias), so we
    # enforce it here too rather than silently inventing one from the id.
    label = entry.get("label")
    if not isinstance(label, str) or not label:
        logger.warning("Connection %(cid)r has no label; skipping", {"cid": cid})
        return None

    type_choice = _cascade(entry.get("type"))
    if type_choice is None:
        return None
    type_name, type_value = type_choice

    if type_name != "livestatus" or not isinstance(type_value, dict):
        return None

    socket_path: str | None = None
    host: str | None = None
    port: int | None = None
    tls = True
    tls_verify = True
    target = _cascade(type_value.get("target"))
    if target is not None:
        target_name, target_value = target
        if target_name == "socket" and isinstance(target_value, dict):
            socket_path = target_value.get("socket_path")
        elif target_name == "tcp" and isinstance(target_value, dict):
            host = target_value.get("host")
            port = target_value.get("port")
            tls = bool(target_value.get("tls", True))
            tls_verify = bool(target_value.get("tls_verify", True))

    automation_user: str | None = None
    automation_secret: str | None = None
    metric_history = _cascade(type_value.get("metric_history"))
    if metric_history is not None and metric_history[0] == "rest_api":
        creds = metric_history[1]
        if isinstance(creds, dict):
            automation_user = creds.get("automation_user")
            automation_secret = _resolve_secret(creds.get("automation_secret"))

    try:
        return ConnectionConfig(
            id=cid,
            type="livestatus",
            label=label,
            socket_path=socket_path,
            host=host,
            port=port,
            tls=tls,
            tls_verify=tls_verify,
            timeout=float(type_value.get("timeout", 10)),
            checkmk_url=type_value.get("checkmk_url") or None,
            automation_user=automation_user,
            automation_secret=automation_secret,
        )
    except Exception as exc:
        logger.warning(
            "Skipping invalid connection %(cid)r: %(exc)s",
            {"cid": cid, "exc": exc},
        )
        return None


def connections_from_global(raw: object) -> list[ConnectionConfig]:
    """Flatten the whole ``maps_connections`` list; skip malformed entries."""
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        return []
    out: list[ConnectionConfig] = []
    for entry in raw:
        if isinstance(entry, Mapping):
            cfg = connection_form_to_config(entry)
            if cfg is not None:
                out.append(cfg)
    return out

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

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from cmk.maps.backend.core.config import Settings, settings
from cmk.maps.backend.schemas.connection import ConnectionConfig, REDACTED_SECRET
from cmk.maps.shared.defaults import DEFAULT_CONNECTION_TIMEOUT
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


def _secret_named(value: object) -> str | None:
    return None if value is None else REDACTED_SECRET


def connection_form_to_config(
    entry: Mapping[str, object], *, resolve_secrets: bool = True, site: Settings = settings
) -> ConnectionConfig | None:
    """Flatten one ``maps_connections`` list entry into a ConnectionConfig.

    Returns ``None`` for a malformed entry (logged) so one bad record cannot
    abort loading the rest. Without ``resolve_secrets`` a configured secret is
    only named, as :data:`REDACTED_SECRET`.
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
    checkmk_url = type_value.get("checkmk_url") or None
    target = _cascade(type_value.get("target"))
    if target is not None:
        target_name, target_value = target
        if target_name == "local":
            socket_path = str(Path(site.checkmk_omd_root) / "tmp" / "run" / "live")
            checkmk_url = checkmk_url or f"/{site.checkmk_site}/check_mk"
        elif target_name == "socket" and isinstance(target_value, dict):
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
            automation_secret = (_resolve_secret if resolve_secrets else _secret_named)(
                creds.get("automation_secret")
            )

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
            timeout=float(type_value.get("timeout", DEFAULT_CONNECTION_TIMEOUT)),
            checkmk_url=checkmk_url,
            automation_user=automation_user,
            automation_secret=automation_secret,
        )
    except Exception as exc:
        logger.warning(
            "Skipping invalid connection %(cid)r: %(exc)s",
            {"cid": cid, "exc": exc},
        )
        return None


def connections_from_global(raw: object, *, resolve_secrets: bool = True) -> list[ConnectionConfig]:
    """Flatten the whole ``maps_connections`` list; skip malformed entries and
    every but the first entry of an ID."""
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        return []
    out: dict[str, ConnectionConfig] = {}
    for entry in raw:
        if (
            isinstance(entry, Mapping)
            and (cfg := connection_form_to_config(entry, resolve_secrets=resolve_secrets))
            is not None
        ):
            if cfg.id in out:
                logger.warning("Skipping a second connection %(cid)r", {"cid": cfg.id})
                continue
            out[cfg.id] = cfg
    return list(out.values())

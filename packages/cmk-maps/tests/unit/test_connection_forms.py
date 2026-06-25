#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI↔daemon contract: flattening the ``maps_connections`` global into ConnectionConfig.

Pins the exact FormSpec ("form") shape WATO writes for a connection — the
``type`` / ``target`` / ``metric_history`` CascadingSingleChoice tuples and the
``automation_secret`` password-store reference — and verifies the daemon
flattens it to ConnectionConfig and resolves the secret.
"""

from __future__ import annotations

from cmk.maps.backend.services import connection_forms

# An "explicit_password" password-store value resolves to its inline value
# without needing the on-disk store (the GUI's "explicit" choice).
_EXPLICIT_SECRET = ("cmk_postprocessed", "explicit_password", ("", "s3cr3t"))


def test_socket_connection() -> None:
    entry = {
        "id": "local",
        "label": "Local",
        "type": (
            "livestatus",
            {
                "target": ("socket", {"socket_path": "/omd/sites/x/tmp/run/live"}),
                "timeout": 10,
                "metric_history": ("livestatus", None),
            },
        ),
    }
    cfg = connection_forms.connection_form_to_config(entry)
    assert cfg is not None
    assert cfg.id == "local"
    assert cfg.socket_path == "/omd/sites/x/tmp/run/live"
    assert cfg.host is None
    assert cfg.automation_secret is None


def test_tcp_connection_with_rest_secret() -> None:
    entry = {
        "id": "remote",
        "label": "Remote",
        "type": (
            "livestatus",
            {
                "target": (
                    "tcp",
                    {"host": "mon.example", "port": 6557, "tls": True, "tls_verify": True},
                ),
                "timeout": 20,
                "checkmk_url": "/remote/check_mk",
                "metric_history": (
                    "rest_api",
                    {"automation_user": "automation", "automation_secret": _EXPLICIT_SECRET},
                ),
            },
        ),
    }
    cfg = connection_forms.connection_form_to_config(entry)
    assert cfg is not None
    assert cfg.host == "mon.example"
    assert cfg.port == 6557
    assert cfg.tls is True and cfg.tls_verify is True
    assert cfg.checkmk_url == "/remote/check_mk"
    assert cfg.automation_user == "automation"
    # The password-store reference must be resolved to plaintext for the daemon.
    assert cfg.automation_secret == "s3cr3t"


def test_unknown_backend_type_skipped() -> None:
    # Only ``livestatus`` is a supported backend type; anything else is skipped
    # rather than crashing the load of the remaining connections.
    assert (
        connection_forms.connection_form_to_config(
            {"id": "demo", "label": "Demo", "type": ("test", None)}
        )
        is None
    )


def test_malformed_entry_skipped() -> None:
    assert connection_forms.connection_form_to_config({"label": "no id"}) is None
    # ``label`` is required (like a site's alias): an entry without one is skipped.
    assert connection_forms.connection_form_to_config({"id": "no-label"}) is None
    assert connection_forms.connection_form_to_config({"id": "x", "label": ""}) is None
    assert connection_forms.connections_from_global("not-a-list") == []
    assert connection_forms.connections_from_global([{"bad": 1}, None]) == []

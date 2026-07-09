#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The GUI↔daemon ``maps_connections`` shape contract, pinned end to end.

The GUI owns the ``maps_connections`` global as a FormSpec
(:func:`cmk.maps.gui.form_specs.connections.connections_list_spec`); WATO writes
its serialized value to the Maps config domain's ``global.mk`` in that FormSpec
shape. The daemon reads that value back read-only and flattens it into runtime
:class:`ConnectionConfig` objects
(:func:`cmk.maps.backend.services.connection_forms.connections_from_global`) —
it deliberately knows the FormSpec serialization (cascade discriminators, dict
keys, the password-store secret container).

That cross-boundary coupling is the risk: rename a FormSpec key or a cascade
name on the GUI side and the daemon would silently drop connections at runtime.
This test feeds the *same* stored value to both sides — the real FormSpec
visitor validates it (so GUI-side drift fails ``validate``) and the real daemon
flattener parses it (so daemon-side drift fails the config assertions). Neither
side is mocked, so the two cannot drift apart without breaking CI.
"""

from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.maps.backend.schemas.connection import ConnectionConfig
from cmk.maps.backend.services.connection_forms import connections_from_global
from cmk.maps.gui.form_specs.connections import connections_list_spec

# One stored ``maps_connections`` value exercising every cascade branch the
# daemon flattener understands: livestatus over a Unix socket, livestatus over
# TCP, and a Nagios/Raw connection whose metric history rides the REST API (with
# an explicit password-store secret). Cascades are ``[name, value]`` lists — the
# shape the FormSpec disk serialization emits and ``exec_mk_file`` reads back.
_STORED_CONNECTIONS = [
    {
        "id": "prod",
        "label": "Production",
        "type": [
            "livestatus",
            {
                "target": ["socket", {"socket_path": "/omd/sites/prod/tmp/run/live"}],
                "timeout": 10,
                "checkmk_url": "/prod/check_mk",
                "metric_history": ["livestatus", None],
            },
        ],
    },
    {
        "id": "remote",
        "label": "Remote datacenter",
        "type": [
            "livestatus",
            {
                "target": [
                    "tcp",
                    {"host": "ls.example.com", "port": 6557, "tls": True, "tls_verify": True},
                ],
                "timeout": 15,
                "metric_history": ["livestatus", None],
            },
        ],
    },
    {
        "id": "raw",
        "label": "Raw core",
        "type": [
            "livestatus",
            {
                "target": [
                    "tcp",
                    {"host": "raw.example.com", "port": 6557, "tls": False, "tls_verify": False},
                ],
                "timeout": 10,
                "metric_history": [
                    "rest_api",
                    {
                        "automation_user": "automation",
                        "automation_secret": [
                            "cmk_postprocessed",
                            "explicit_password",
                            ["pwid", "s3cr3t"],
                        ],
                    },
                ],
            },
        ],
    },
]

_EXPECTED_CONFIGS = [
    ConnectionConfig(
        id="prod",
        type="livestatus",
        label="Production",
        socket_path="/omd/sites/prod/tmp/run/live",
        timeout=10.0,
        checkmk_url="/prod/check_mk",
    ),
    ConnectionConfig(
        id="remote",
        type="livestatus",
        label="Remote datacenter",
        host="ls.example.com",
        port=6557,
        tls=True,
        tls_verify=True,
        timeout=15.0,
    ),
    ConnectionConfig(
        id="raw",
        type="livestatus",
        label="Raw core",
        host="raw.example.com",
        port=6557,
        tls=False,
        tls_verify=False,
        timeout=10.0,
        automation_user="automation",
        automation_secret="s3cr3t",
    ),
]


def test_gui_formspec_accepts_the_value_the_daemon_parses() -> None:
    # GUI side: the real FormSpec accepts this stored shape unchanged. A renamed
    # dict key or cascade discriminator on the GUI side surfaces here.
    spec = connections_list_spec(monitoring_core="cmc")
    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=False))
    assert visitor.validate(RawDiskData(_STORED_CONNECTIONS)) == []


def test_daemon_flattens_the_stored_value_into_runtime_configs() -> None:
    # Daemon side: the same stored shape flattens into the runtime configs,
    # including resolving the explicit password-store secret to plaintext.
    assert connections_from_global(_STORED_CONNECTIONS) == _EXPECTED_CONFIGS

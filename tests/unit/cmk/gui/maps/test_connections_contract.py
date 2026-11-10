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

from collections.abc import Iterator

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.maps.backend.schemas.connection import ConnectionConfig
from cmk.maps.backend.services.connection_forms import connections_from_global
from cmk.maps.gui._config_variables import connections_form_spec
from cmk.maps.gui.form_specs.connections import connections_list_spec
from cmk.utils import password_store

# One stored ``maps_connections`` value exercising every cascade branch the
# daemon flattener understands: livestatus over a Unix socket, livestatus over
# TCP, and a Nagios/Raw connection whose metric history rides the REST API (with
# a password-store secret). Cascades are ``[name, value]`` lists — the
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
                            "stored_password",
                            ["maps-raw", ""],
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


pytestmark = pytest.mark.usefixtures("stored_secret")


@pytest.fixture(name="stored_secret")
def fixture_stored_secret() -> Iterator[None]:
    password_store.save({"maps-raw": "s3cr3t"}, password_store.pending_secrets_path_site())
    yield
    password_store.pending_secrets_path_site().unlink(missing_ok=True)


def test_gui_formspec_accepts_the_value_the_daemon_parses() -> None:
    # GUI side: the real FormSpec accepts this stored shape unchanged. A renamed
    # dict key or cascade discriminator on the GUI side surfaces here.
    spec = connections_list_spec(monitoring_core="cmc", secret_usable=lambda _pid: True)
    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=False))
    assert visitor.validate(RawDiskData(_STORED_CONNECTIONS)) == []


def test_daemon_flattens_the_stored_value_into_runtime_configs() -> None:
    # Daemon side: the same stored shape flattens into the runtime configs,
    # including resolving the password-store secret to plaintext.
    assert connections_from_global(_STORED_CONNECTIONS) == _EXPECTED_CONFIGS


_STORED_TWICE = [*_STORED_CONNECTIONS, {**_STORED_CONNECTIONS[1], "label": "Second"}]


@pytest.mark.usefixtures("request_context", "with_user_login")
def test_gui_formspec_refuses_an_id_used_twice() -> None:
    spec = connections_list_spec(monitoring_core="cmc", secret_usable=lambda _pid: True)
    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=False))
    assert [m.message for m in visitor.validate(RawDiskData(_STORED_TWICE))] == [
        'The connection ID "remote" is used more than once.'
    ]


def test_daemon_keeps_the_first_connection_of_an_id() -> None:
    assert connections_from_global(_STORED_TWICE) == _EXPECTED_CONFIGS


_REFUSED = [
    (
        'The password of the connection "raw" has either been removed or you are not permitted '
        "to use it. Please choose another one."
    )
]


@pytest.mark.usefixtures("request_context", "with_user_login")
def test_gui_formspec_refuses_a_password_the_user_may_not_use() -> None:
    spec = connections_list_spec(monitoring_core="cmc", secret_usable=lambda _pid: False)
    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=False))
    assert [m.message for m in visitor.validate(RawDiskData(_STORED_CONNECTIONS))] == _REFUSED


@pytest.mark.usefixtures("request_context", "with_user_login")
def test_a_connection_keeps_no_password_the_user_may_not_use() -> None:
    visitor = get_visitor(
        connections_form_spec(), VisitorOptions(migrate_values=True, mask_values=False)
    )

    messages = [m.message for m in visitor.validate(RawDiskData(_STORED_CONNECTIONS))]

    assert messages == _REFUSED


@pytest.mark.usefixtures("request_context", "with_user_login")
def test_gui_formspec_keeps_rest_credentials_with_the_connection() -> None:
    elsewhere = [
        {
            "id": "raw",
            "label": "Raw core",
            "type": [
                "livestatus",
                {
                    "target": [
                        "tcp",
                        {"host": "raw.example.com", "port": 6557, "tls": True, "tls_verify": True},
                    ],
                    "timeout": 10,
                    "checkmk_url": "https://other.example.com/check_mk",
                    "metric_history": [
                        "rest_api",
                        {
                            "automation_user": "automation",
                            "automation_secret": [
                                "cmk_postprocessed",
                                "stored_password",
                                ["maps-raw", ""],
                            ],
                        },
                    ],
                },
            ],
        }
    ]
    spec = connections_list_spec(monitoring_core="cmc", secret_usable=lambda _pid: True)
    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=False))
    assert [m.message for m in visitor.validate(RawDiskData(elsewhere))] == [
        (
            "With REST API credentials, the Checkmk URL must be a path on this site "
            "or name the host of the TCP target."
        )
    ]

#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.podman.rulesets.agent_plugin_config import _migrate


def test_migrate_invalid_type() -> None:
    with pytest.raises(ValueError):
        _migrate(42)


@pytest.mark.parametrize(
    "input_value, expected",
    [
        pytest.param(
            {},
            {"connection_method": ("api", ("auto", None))},
            id="empty dict defaults to api+auto",
        ),
        pytest.param(
            {"socket_detection": ("auto", None)},
            {"connection_method": ("api", ("auto", None))},
            id="old format: auto detection",
        ),
        pytest.param(
            {"socket_detection": ("only_root_socket", None)},
            {"connection_method": ("api", ("only_root_socket", None))},
            id="old format: only root socket",
        ),
        pytest.param(
            {"socket_detection": ("only_user_sockets", None)},
            {"connection_method": ("api", ("only_user_sockets", None))},
            id="old format: only user sockets",
        ),
        pytest.param(
            {"socket_detection": ("manual", ["/run/podman/podman.sock"])},
            {"connection_method": ("api", ("manual", ["/run/podman/podman.sock"]))},
            id="old format: manual socket paths",
        ),
        pytest.param(
            {
                "deploy": True,
                "socket_detection": ("auto", None),
                "piggyback_name_method": "name_id",
            },
            {
                "deploy": True,
                "connection_method": ("api", ("auto", None)),
                "piggyback_name_method": "name_id",
            },
            id="old format: preserves other fields",
        ),
        pytest.param(
            {
                "deploy": True,
                "connection_method": ("api", ("auto", None)),
                "piggyback_name_method": "nodename_name",
            },
            {
                "deploy": True,
                "connection_method": ("api", ("auto", None)),
                "piggyback_name_method": "nodename_name",
            },
            id="new format: api is noop",
        ),
        pytest.param(
            {"deploy": True, "connection_method": ("cli", None)},
            {"deploy": True, "connection_method": ("cli", None)},
            id="new format: cli is noop",
        ),
    ],
)
def test_migrate(input_value: object, expected: object) -> None:
    assert _migrate(input_value) == expected

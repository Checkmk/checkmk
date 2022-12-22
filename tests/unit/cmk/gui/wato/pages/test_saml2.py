#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package


from typing import Any, Iterable, NamedTuple

import pytest

from cmk.gui.http import Request
from cmk.gui.wato.pages.saml2 import ModeSAML2Config


class Variables(NamedTuple):
    http: dict[str, str]
    valuespec: dict[str, Any]
    serialised: dict[str, Any]


@pytest.fixture(name="config_variables")
def fixture_config_variables() -> Variables:
    return Variables(
        http={
            "vs_p_type": "saml2",
            "vs_p_version": "1.0.0",
            "vs_p_id": "123",
            "vs_p_description": "",
            "vs_p_comment": "",
            "vs_p_docu_url": "",
            "vs_p_idp_metadata_endpoint": "https://myidp.com",
            "vs_p_checkmk_server_url": "https://mycheckmk.com",
            "vs_p_connection_timeout_0": "12",
            "vs_p_connection_timeout_1": "12",
            "vs_p_user_id_attribute": "username",
            "vs_p_create_users_on_login": "on",
        },
        valuespec={
            "type": "saml2",
            "version": "1.0.0",
            "id": "123",
            "description": "",
            "disabled": False,
            "docu_url": "",
            "comment": "",
            "connection_timeout": (12, 12),
            "checkmk_server_url": "https://mycheckmk.com",
            "idp_metadata_endpoint": "https://myidp.com",
            "user_id_attribute": "username",
            "create_users_on_login": True,
        },
        serialised={
            "type": "saml2",
            "version": "1.0.0",
            "id": "123",
            "comment": "",
            "description": "",
            "disabled": False,
            "docu_url": "",
            "interface_config": {
                "checkmk_server_url": "https://mycheckmk.com",
                "connection_timeout": (12, 12),
                "idp_metadata_endpoint": "https://myidp.com",
                "user_id_attribute": "username",
            },
            "create_users_on_login": True,
        },
    )


@pytest.fixture(name="mocked_request")
def fixture_mocked_request(
    monkeypatch: pytest.MonkeyPatch, config_variables: Variables
) -> Iterable[Request]:
    mock_request = Request(environ={})
    for k, v in config_variables.http.items():
        mock_request.set_var(k, v)

    monkeypatch.setattr("cmk.gui.valuespec.request", mock_request)
    yield mock_request


def test_to_config_file(mocked_request: Request, config_variables: Variables) -> None:
    wato_mode = ModeSAML2Config()
    valuespec_config = wato_mode._user_input()
    actual_serialised_config = wato_mode.to_config_file(valuespec_config)

    assert valuespec_config == config_variables.valuespec
    assert actual_serialised_config == config_variables.serialised


def test_from_config_file(monkeypatch: pytest.MonkeyPatch, config_variables: Variables) -> None:
    monkeypatch.setattr(
        "cmk.gui.plugins.userdb.utils.active_config.user_connections", [config_variables.serialised]
    )
    wato_mode = ModeSAML2Config()
    config = wato_mode.from_config_file()

    assert config == config_variables.valuespec

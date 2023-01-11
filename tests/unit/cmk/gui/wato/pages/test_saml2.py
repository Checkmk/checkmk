#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package


from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from cmk.utils.paths import (
    saml2_custom_signature_private_keyfile,
    saml2_custom_signature_public_keyfile,
    saml2_signature_private_keyfile,
    saml2_signature_public_keyfile,
)

from cmk.gui.http import Request
from cmk.gui.wato.pages.saml2 import ModeEditSAML2Config


class Variables(NamedTuple):
    http: Mapping[str, str]
    valuespec: Mapping[str, Any]
    serialised: Mapping[str, Any]


CERTIFICATE_DIR = Path(__file__).parent.parent.parent / "userdb/saml2/certificate_files"
PRIVATE_KEY = Path(CERTIFICATE_DIR / "signature_private.pem").read_text()
CERTIFICATE = Path(CERTIFICATE_DIR / "signature_public.pem").read_text()


@pytest.fixture(
    name="signature_certificate",
    params=[
        Variables(
            http={
                "vs_p_signature_certificate_sel": "0",
                "vs_p_signature_certificate_1_0": "",
                "vs_p_signature_certificate_1_1": "",
            },
            valuespec={
                "signature_certificate": "default",
            },
            serialised={
                "signature_certificate": {
                    "private": str(saml2_signature_private_keyfile),
                    "public": str(saml2_signature_public_keyfile),
                },
            },
        ),
        Variables(
            http={
                "vs_p_signature_certificate_sel": "1",
                "vs_p_signature_certificate_1_0": PRIVATE_KEY,
                "vs_p_signature_certificate_1_1": CERTIFICATE,
            },
            valuespec={
                "signature_certificate": ("custom", (PRIVATE_KEY, CERTIFICATE)),
            },
            serialised={
                "signature_certificate": {
                    "private": str(saml2_custom_signature_private_keyfile),
                    "public": str(saml2_custom_signature_public_keyfile),
                },
            },
        ),
    ],
    ids=[
        "Default: use Checkmk certificate",
        "Use own certificates",
    ],
)
def fixture_signature_certificate(request: pytest.FixtureRequest) -> Variables:
    return request.param


@pytest.fixture(name="config_variables")
def fixture_config_variables(signature_certificate: Variables) -> Variables:
    return Variables(
        http={
            "vs_p_type": "saml2",
            "vs_p_version": "1.0.0",
            "vs_p_id": "123",
            "vs_p_name": "härbärt",
            "vs_p_description": "",
            "vs_p_comment": "",
            "vs_p_docu_url": "",
            "vs_p_idp_metadata_endpoint": "https://myidp.com",
            "vs_p_checkmk_server_url": "https://mycheckmk.com",
            "vs_p_connection_timeout_0": "12",
            "vs_p_connection_timeout_1": "12",
            **signature_certificate.http,
            "vs_p_user_id_attribute": "username",
        },
        valuespec={
            "type": "saml2",
            "version": "1.0.0",
            "id": "123",
            "name": "härbärt",
            "description": "",
            "disabled": False,
            "docu_url": "",
            "comment": "",
            "connection_timeout": (12, 12),
            "checkmk_server_url": "https://mycheckmk.com",
            "idp_metadata_endpoint": "https://myidp.com",
            **signature_certificate.valuespec,
            "user_id_attribute": "username",
        },
        serialised={
            "type": "saml2",
            "version": "1.0.0",
            "id": "123",
            "name": "härbärt",
            "comment": "",
            "description": "",
            "disabled": False,
            "docu_url": "",
            "interface_config": {
                "checkmk_server_url": "https://mycheckmk.com",
                "connection_timeout": [12, 12],
                "idp_metadata_endpoint": "https://myidp.com",
                "user_id_attribute": "username",
                **signature_certificate.serialised,
            },
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


def test_to_config_file(
    monkeypatch: pytest.MonkeyPatch, mocked_request: Request, config_variables: Variables
) -> None:
    monkeypatch.setattr("pathlib.Path.write_text", lambda s, t: None)

    wato_mode = ModeEditSAML2Config()
    valuespec_config = wato_mode._valuespec.from_html_vars(wato_mode._html_valuespec_param_prefix)
    actual_serialised_config = wato_mode.to_config_file(valuespec_config)

    assert valuespec_config == config_variables.valuespec
    assert actual_serialised_config == config_variables.serialised


def test_from_config_file(monkeypatch: pytest.MonkeyPatch, config_variables: Variables) -> None:
    file_content = {
        str(saml2_custom_signature_private_keyfile): PRIVATE_KEY,
        str(saml2_custom_signature_public_keyfile): CERTIFICATE,
    }
    monkeypatch.setattr("pathlib.Path.read_text", lambda s: file_content[str(s)])
    monkeypatch.setattr(
        "cmk.gui.plugins.userdb.utils.active_config.user_connections", [config_variables.serialised]
    )
    wato_mode = ModeEditSAML2Config()
    config = wato_mode.from_config_file(connection_id=config_variables.valuespec["id"])

    assert config == config_variables.valuespec

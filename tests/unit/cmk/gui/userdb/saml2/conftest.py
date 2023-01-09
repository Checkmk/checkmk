#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def xmlsec1_binary_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock that the xmlsec1 binary exists and is in PATH
    monkeypatch.setattr("saml2.sigver.get_xmlsec_binary", lambda p: "xmlsec1")
    monkeypatch.setattr("os.path.exists", lambda p: True)


@pytest.fixture(scope="session", name="signature_certificate_paths")
def fixture_signature_certificate_paths() -> tuple[Path, Path]:
    # Were generated with
    # openssl req -x509 -newkey rsa:1024 -days +3650 -subj "/CN=saml2-test-sign/O=checkmk-testing/C=DE" -keyout signature_private.pem -out signature_public.pem -sha256 -nodes
    # 1024 bit is used for performance reasons
    cert_dir = Path(__file__).parent / "certificate_files"
    return Path(cert_dir / "signature_private.pem"), Path(cert_dir / "signature_public.pem")


@pytest.fixture(name="raw_config")
def fixture_raw_config(signature_certificate_paths: tuple[Path, Path]) -> dict[str, Any]:
    private_keyfile_path, public_keyfile_path = signature_certificate_paths
    return {
        "type": "saml2",
        "version": "1.0.0",
        "id": "uuid123",
        "description": "",
        "comment": "",
        "docu_url": "",
        "disabled": False,
        "interface_config": {
            "connection_timeout": [12, 12],
            "checkmk_server_url": "http://localhost",
            "idp_metadata_endpoint": "http://localhost:8080/simplesaml/saml2/idp/metadata.php",
            "user_id_attribute": "username",
            "signature_certificate": {
                "private": str(private_keyfile_path),
                "public": str(public_keyfile_path),
            },
        },
        "create_users_on_login": False,
    }


@pytest.fixture(autouse=True)
def url_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.gui.userdb.saml2.interface.url_prefix", lambda: "/heute/")


@pytest.fixture(name="xml_files_path", scope="session")
def fixture_xml_files_path() -> Path:
    return Path(__file__).parent / "xml_files"


@pytest.fixture
def metadata_from_idp(monkeypatch: pytest.MonkeyPatch, xml_files_path: Path) -> None:
    with open(xml_files_path / "identity_provider_metadata.xml", "r") as f:
        metadata_str = f.read()
    monkeypatch.setattr(
        "cmk.gui.userdb.saml2.interface._metadata_from_idp", lambda c, t: metadata_str
    )

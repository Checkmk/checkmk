#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any, Iterable

import pytest
from saml2.cryptography.asymmetric import load_pem_private_key


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


@pytest.fixture(scope="session", name="signature_certificate")
def fixture_signature_certificate(
    signature_certificate_paths: tuple[Path, Path]
) -> Iterable[dict[str, str]]:
    private_keyfile_path, public_keyfile_path = signature_certificate_paths

    private_key_content = private_keyfile_path.read_bytes()
    public_key_content = public_keyfile_path.read_text()

    # The following awkwardness is done for performance reasons to patch a few slow spots with the
    # pysaml2 client. Note:

    # - 'load_pem_private_key' takes ages (!)
    # - the public key is somehow expected without a header by subsequent functions within the
    #   pysaml2 module
    in_memory_variant = {
        str(private_keyfile_path): load_pem_private_key(private_key_content),
        str(public_keyfile_path): "".join(public_key_content.splitlines()[1:-1]),
    }

    yield in_memory_variant


@pytest.fixture(autouse=True)
def certificates(monkeypatch: pytest.MonkeyPatch, signature_certificate: dict[str, str]) -> None:
    monkeypatch.setattr(
        "saml2.sigver.import_rsa_key_from_file",
        lambda f: signature_certificate[f],
    )
    monkeypatch.setattr("saml2.cert.read_cert_from_file", lambda f, _: signature_certificate[f])
    monkeypatch.setattr("saml2.sigver.read_cert_from_file", lambda f, _: signature_certificate[f])
    monkeypatch.setattr(
        "saml2.metadata.read_cert_from_file",
        lambda f, *_: signature_certificate.get(
            f
        ),  # the .get method is used because encryption certificates are not yet implemented
    )


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


@pytest.fixture(name="xml_files_path")
def fixture_xml_files_path() -> Path:
    return Path(__file__).parent / "xml_files"


@pytest.fixture
def metadata_from_idp(monkeypatch: pytest.MonkeyPatch, xml_files_path: Path) -> None:
    with open(xml_files_path / "identity_provider_metadata.xml", "r") as f:
        metadata_str = f.read()
    monkeypatch.setattr(
        "cmk.gui.userdb.saml2.interface._metadata_from_idp", lambda c, t: metadata_str
    )

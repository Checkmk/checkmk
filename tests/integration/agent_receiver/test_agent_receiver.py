#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from http import HTTPStatus
from pathlib import Path
from typing import NamedTuple

import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from tests.testlib.site import Site


@pytest.fixture(scope="session", name="agent_receiver_port")
def agent_receiver_port_fixture(site: Site) -> int:
    return int(
        site.openapi.request(
            method="get",
            url="domain-types/internal/actions/discover-receiver/invoke",
        ).text
    )


@pytest.fixture(scope="session", name="agent_receiver_url")
def agent_receiver_url_fixture(site: Site, agent_receiver_port: int) -> str:
    return f"https://{site.http_address}:{agent_receiver_port}/{site.id}/agent-receiver"


def test_uuid_check_client_certificate(agent_receiver_url: str) -> None:
    # try to acces the status endpoint by explicitly writing a fake UUID into the HTTP header
    uuid_ = uuid.uuid4()
    agent_receiver_response = requests.get(
        f"{agent_receiver_url}/registration_status/{uuid_}",
        headers={"verified-uuid": str(uuid_)},
        verify=False,
    )
    assert agent_receiver_response.status_code == HTTPStatus.BAD_REQUEST
    assert (
        "Verified client UUID (missing: no client certificate provided) does not match UUID in URL"
        in agent_receiver_response.json()["detail"]
    )


def _generate_private_key(size: int = 2048) -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=size,
    )


def _generate_csr(private_key: rsa.RSAPrivateKey, uuid_: str) -> str:
    return (
        x509.CertificateSigningRequestBuilder()
        .subject_name(
            x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, uuid_),
                ]
            )
        )
        .sign(
            private_key,
            hashes.SHA256(),
        )
        .public_bytes(serialization.Encoding.PEM)
        .decode("utf-8")
    )


class KeyPairInfo(NamedTuple):
    uuid_: str
    private_key_path: Path
    public_key_path: Path

    def cert_tuple(self) -> tuple[str, str]:
        return str(self.public_key_path), str(self.private_key_path)


@pytest.fixture(scope="module", name="paired_keypair")
def paired_keypair_fixture(
    agent_receiver_url: str,
    site: Site,
    tmp_path_factory: pytest.TempPathFactory,
) -> KeyPairInfo:
    uuid_ = str(uuid.uuid4())
    private_key = _generate_private_key()
    csr = _generate_csr(private_key, uuid_)

    agent_receiver_response = requests.post(
        f"{agent_receiver_url}/pairing",
        auth=("cmkadmin", site.admin_password),
        json={"csr": csr},
        verify=False,
    )
    assert agent_receiver_response.status_code == 200

    private_key_path = tmp_path_factory.mktemp("certs") / "private_key.key"
    with private_key_path.open("wb") as private_key_file:
        private_key_file.write(
            # mypy claims private_bytes is not a thing, docs and reality say otherwise...
            private_key.private_bytes(  # type: ignore[attr-defined]
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    public_key_path = tmp_path_factory.mktemp("certs") / "public.pem"
    with public_key_path.open("w") as public_key_file:
        public_key_file.write(agent_receiver_response.json()["client_cert"])

    return KeyPairInfo(
        uuid_=uuid_,
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )


def test_failing_pairing_no_uuid(agent_receiver_url: str, site: Site) -> None:
    uuid_ = "not a uuid"
    private_key = _generate_private_key()
    csr = _generate_csr(private_key, uuid_)

    agent_receiver_response = requests.post(
        f"{agent_receiver_url}/pairing",
        auth=("cmkadmin", site.admin_password),
        json={"csr": csr},
        verify=False,
    )
    assert agent_receiver_response.status_code == 400


def test_registration_status_not_registered(
    agent_receiver_url: str, paired_keypair: KeyPairInfo
) -> None:
    response = requests.get(
        f"{agent_receiver_url}/registration_status/{paired_keypair.uuid_}",
        cert=paired_keypair.cert_tuple(),
        verify=False,
    )
    assert response.json()["detail"] == "Host is not registered"


def test_register_with_hostname_non_existing(
    agent_receiver_url: str, paired_keypair: KeyPairInfo, site: Site
) -> None:
    response = requests.post(
        f"{agent_receiver_url}/register_with_hostname",
        auth=("cmkadmin", site.admin_password),
        json={
            "uuid": paired_keypair.uuid_,
            "host_name": "non-existing",
        },
        verify=False,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Host non-existing does not exist."

    response = requests.post(
        f"{agent_receiver_url}/register_with_hostname",
        auth=("cmkadmin", site.admin_password),
        json={
            "uuid": paired_keypair.uuid_,
            "host_name": "../../../dirtraversal",
        },
        verify=False,
    )
    assert response.status_code == 400

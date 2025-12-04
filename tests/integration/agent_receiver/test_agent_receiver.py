#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ssl
import uuid
from http import HTTPStatus
from pathlib import Path
from typing import NamedTuple

import pytest
import requests
from cryptography.hazmat.primitives import asymmetric, serialization
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.x509 import (
    CertificateSigningRequest,
    CertificateSigningRequestBuilder,
    load_pem_x509_certificate,
    Name,
    NameAttribute,
)
from cryptography.x509.oid import NameOID

# TODO: Integration tests are not allowed to import application code. We need to get rid of this
from cmk.agent_receiver.lib.certs import (  # astrein: disable=cmk-module-layer-violation
    current_time_naive,
    serialize_to_pem,
    sign_csr,
)
from tests.testlib.site import Site
from tests.testlib.tls import CMKTLSError, tls_connect


# Copied from tests/unit/agent_receiver/certs.py to make cmk-agent-receiver/tests self contained
def generate_csr_pair(cn: str) -> tuple[asymmetric.rsa.RSAPrivateKey, CertificateSigningRequest]:
    private_key = asymmetric.rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return (
        private_key,
        CertificateSigningRequestBuilder()
        .subject_name(
            Name(
                [
                    NameAttribute(NameOID.COMMON_NAME, cn),
                ]
            )
        )
        .sign(
            private_key,
            SHA256(),
        ),
    )


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


@pytest.fixture(scope="session", name="site_ca")
def site_ca_fixture(site: Site, tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("ca") / "site.pem"
    path.write_bytes(site.read_file("etc/ssl/ca.pem", encoding=None))
    return path


@pytest.mark.medium_test_chain
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


class KeyPairInfo(NamedTuple):
    uuid_: str
    private_key_path: Path
    public_key_path: Path

    def cert_tuple(self) -> tuple[str, str]:
        return str(self.public_key_path), str(self.private_key_path)


@pytest.fixture(scope="module", name="paired_keypair")
def paired_keypair_fixture(
    site: Site,
    tmp_path_factory: pytest.TempPathFactory,
) -> KeyPairInfo:
    uuid_ = str(uuid.uuid4())
    private_key, csr = generate_csr_pair(uuid_)

    pem_bytes = site.read_file("etc/ssl/agents/ca.pem").encode("utf-8")
    root_cert, root_key = (
        load_pem_x509_certificate(pem_bytes),
        serialization.load_pem_private_key(pem_bytes, None),
    )
    assert isinstance(
        root_key,
        # this is CertificateIssuerPrivateKeyTypes
        asymmetric.ed25519.Ed25519PrivateKey
        | asymmetric.ed448.Ed448PrivateKey
        | asymmetric.rsa.RSAPrivateKey
        | asymmetric.dsa.DSAPrivateKey
        | asymmetric.ec.EllipticCurvePrivateKey,
    )

    private_key_path = tmp_path_factory.mktemp("certs") / "private_key.key"
    with private_key_path.open("wb") as private_key_file:
        private_key_file.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    public_key_path = tmp_path_factory.mktemp("certs") / "public.pem"
    with public_key_path.open("w") as public_key_file:
        public_key_file.write(
            serialize_to_pem(sign_csr(csr, 12, (root_cert, root_key), current_time_naive()))
        )

    return KeyPairInfo(
        uuid_=uuid_,
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )


@pytest.mark.medium_test_chain
def test_failing_pairing_no_uuid(agent_receiver_url: str, site: Site) -> None:
    uuid_ = "not a uuid"
    _key, csr = generate_csr_pair(uuid_)

    agent_receiver_response = requests.post(
        f"{agent_receiver_url}/pairing",
        auth=("cmkadmin", site.admin_password),
        json={"csr": serialize_to_pem(csr)},
        verify=False,
    )
    assert agent_receiver_response.status_code == 400


@pytest.mark.medium_test_chain
def test_registration_status_not_registered(
    agent_receiver_url: str, paired_keypair: KeyPairInfo
) -> None:
    response = requests.get(
        f"{agent_receiver_url}/registration_status/{paired_keypair.uuid_}",
        cert=paired_keypair.cert_tuple(),
        verify=False,
    )
    assert response.json()["detail"] == "Host is not registered"


@pytest.mark.medium_test_chain
def test_register_existing_non_existing(
    agent_receiver_url: str,
    site: Site,
) -> None:
    uuid_ = str(uuid.uuid4())
    csr = generate_csr_pair(uuid_)[1]

    response = requests.post(
        f"{agent_receiver_url}/register_existing",
        auth=("cmkadmin", site.admin_password),
        json={
            "uuid": uuid_,
            "csr": serialize_to_pem(csr),
            "host_name": "non-existing",
        },
        verify=False,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Host non-existing does not exist."

    response = requests.post(
        f"{agent_receiver_url}/register_existing",
        auth=("cmkadmin", site.admin_password),
        json={
            "uuid": uuid_,
            "csr": serialize_to_pem(csr),
            "host_name": "../../../dirtraversal",
        },
        verify=False,
    )
    assert response.status_code == 400


@pytest.mark.medium_test_chain
def test_register_with_hostname_non_existing(
    agent_receiver_url: str,
    site: Site,
) -> None:
    uuid_ = str(uuid.uuid4())

    response = requests.post(
        f"{agent_receiver_url}/register_with_hostname",
        auth=("cmkadmin", site.admin_password),
        json={
            "uuid": uuid_,
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
            "uuid": uuid_,
            "host_name": "../../../dirtraversal",
        },
        verify=False,
    )
    assert response.status_code == 400


UNSUPPORTED_VERSIONS = (ssl.TLSVersion.SSLv3, ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1_1)
SUPPORTED_VERSIONS = (ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3)


@pytest.mark.medium_test_chain
@pytest.mark.parametrize("tls_version", UNSUPPORTED_VERSIONS, ids=lambda v: v.name)
def test_unsupported_tls_versions(
    site: Site, agent_receiver_port: int, site_ca: Path, tls_version: ssl.TLSVersion
) -> None:
    """Test that the receiver rejects old TLS versions."""

    with pytest.raises(CMKTLSError):
        tls_connect(
            site.http_address,
            agent_receiver_port,
            site_ca,
            tls_version,
        )


@pytest.mark.medium_test_chain
@pytest.mark.parametrize("tls_version", SUPPORTED_VERSIONS, ids=lambda v: v.name)
def test_supported_tls_versions(
    site: Site, agent_receiver_port: int, site_ca: Path, tls_version: ssl.TLSVersion
) -> None:
    """Test that the receiver accepts supported TLS versions."""
    tls_connect(
        site.http_address,
        agent_receiver_port,
        site_ca,
        tls_version,
    )


@pytest.mark.medium_test_chain
def test_all_TLS_versions_tested(site: Site, agent_receiver_port: int, site_ca: Path) -> None:
    """Ensure the above tests cover all TLS versions."""
    all_versions = {
        version
        for name, version in ssl.TLSVersion.__members__.items()
        if name.startswith(("SSL", "TLS"))
    }

    assert set(UNSUPPORTED_VERSIONS + SUPPORTED_VERSIONS) == all_versions

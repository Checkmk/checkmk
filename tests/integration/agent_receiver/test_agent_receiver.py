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
from dateutil.relativedelta import relativedelta

from cmk.crypto.certificate import CertificateSigningRequest, CertificateWithPrivateKey
from cmk.crypto.keys import PrivateKey
from cmk.crypto.x509 import SAN, SubjectAlternativeNames, X509Name
from tests.testlib.site import Site
from tests.testlib.tls import CMKTLSError, tls_connect


# Copied from tests/unit/agent_receiver/certs.py to make cmk-agent-receiver/tests self contained
def generate_csr_pair(cn: str) -> tuple[PrivateKey, CertificateSigningRequest]:
    private_key = PrivateKey.generate_rsa(2048)
    return (
        private_key,
        CertificateSigningRequest.create(
            subject_name=X509Name.create(common_name=cn),
            subject_private_key=private_key,
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
@pytest.mark.skip_if_faked_artifacts
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

    root_ca = CertificateWithPrivateKey.load_combined_file_content(
        site.read_file("etc/ssl/agents/ca.pem"),
        passphrase=None,
    )

    private_key_path = tmp_path_factory.mktemp("certs") / "private_key.key"
    with private_key_path.open("wb") as private_key_file:
        private_key_file.write(private_key.dump_pem(None).bytes)
    public_key_path = tmp_path_factory.mktemp("certs") / "public.pem"
    with public_key_path.open("w") as public_key_file:
        public_key_file.write(
            root_ca.sign_csr(
                csr,
                relativedelta(months=12),
                SubjectAlternativeNames([SAN.dns_name(uuid_)]),
            )
            .dump_pem()
            .str
        )

    return KeyPairInfo(
        uuid_=uuid_,
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )


@pytest.mark.medium_test_chain
@pytest.mark.skip_if_faked_artifacts
def test_failing_pairing_no_uuid(agent_receiver_url: str, site: Site) -> None:
    uuid_ = "not a uuid"
    _key, csr = generate_csr_pair(uuid_)

    agent_receiver_response = requests.post(
        f"{agent_receiver_url}/pairing",
        auth=("cmkadmin", site.admin_password),
        json={"csr": csr.dump_pem().str},
        verify=False,
    )
    assert agent_receiver_response.status_code == 400


@pytest.mark.medium_test_chain
@pytest.mark.skip_if_faked_artifacts
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
@pytest.mark.skip_if_faked_artifacts
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
            "csr": csr.dump_pem().str,
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
            "csr": csr.dump_pem().str,
            "host_name": "../../../dirtraversal",
        },
        verify=False,
    )
    assert response.status_code == 400


@pytest.mark.medium_test_chain
@pytest.mark.skip_if_faked_artifacts
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
@pytest.mark.skip_if_faked_artifacts
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
@pytest.mark.skip_if_faked_artifacts
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
@pytest.mark.skip_if_faked_artifacts
def test_all_TLS_versions_tested(site: Site, agent_receiver_port: int, site_ca: Path) -> None:
    """Ensure the above tests cover all TLS versions."""
    all_versions = {
        version
        for name, version in ssl.TLSVersion.__members__.items()
        if name.startswith(("SSL", "TLS"))
    }

    assert set(UNSUPPORTED_VERSIONS + SUPPORTED_VERSIONS) == all_versions

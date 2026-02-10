#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from collections.abc import Callable
from datetime import datetime, UTC
from http import HTTPStatus
from pathlib import Path
from typing import NamedTuple

import pytest
import requests
from cryptography.hazmat.primitives import asymmetric, serialization
from cryptography.hazmat.primitives.asymmetric.types import CertificateIssuerPrivateKeyTypes
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.x509 import (
    BasicConstraints,
    Certificate,
    CertificateBuilder,
    CertificateSigningRequest,
    CertificateSigningRequestBuilder,
    DNSName,
    load_pem_x509_certificate,
    Name,
    NameAttribute,
    random_serial_number,
    SubjectAlternativeName,
)
from cryptography.x509.oid import NameOID
from matplotlib.dates import relativedelta

from tests.testlib.site import Site

# Warning, duplicate code.
# Some of the following functions are also defined in packages/cmk-agent-receiver/cmk/agent_receiver/lib/certs.py
# The integration tests are not allowed to import code directly from the app,
# but we need their functionality here.
# TODO find a better (shared) place for these functions.


def current_time_naive() -> datetime:
    """
    Create a not timezone aware, "naive", datetime at UTC now. This mimics the deprecated
    datetime.utcnow(), but we still need it to be naive because that's what pyca/cryptography
    certificates use. See also https://github.com/pyca/cryptography/issues/9186.
    """
    return datetime.now(tz=UTC).replace(tzinfo=None)


def serialize_to_pem(certificate: Certificate | CertificateSigningRequest) -> str:
    return certificate.public_bytes(serialization.Encoding.PEM).decode()


def extract_cn_from_csr(csr: CertificateSigningRequest) -> str:
    v = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    assert isinstance(v, str)
    return v


def sign_csr(
    csr: CertificateSigningRequest,
    lifetime_in_months: int,
    keypair: tuple[Certificate, CertificateIssuerPrivateKeyTypes],
    valid_from: datetime,
) -> Certificate:
    root_cert, root_key = keypair
    return (
        CertificateBuilder()
        .subject_name(csr.subject)
        .public_key(csr.public_key())
        .serial_number(random_serial_number())
        .not_valid_before(valid_from)
        .not_valid_after(valid_from + relativedelta(months=lifetime_in_months))
        .issuer_name(root_cert.subject)
        .add_extension(
            SubjectAlternativeName([DNSName(extract_cn_from_csr(csr))]),
            critical=False,
        )
        .add_extension(
            BasicConstraints(
                ca=False,
                path_length=None,
            ),
            critical=True,
        )
        .sign(
            root_key,
            SHA256(),
        )
    )


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


class KeyPairInfo(NamedTuple):
    uuid_: str
    private_key_path: Path
    public_key_path: Path
    csr_pem: str

    def cert_tuple(self) -> tuple[str, str]:
        return str(self.public_key_path), str(self.private_key_path)


@pytest.fixture(scope="session", name="agent_receiver_port")
def agent_receiver_port_fixture(site: Site) -> int:
    return int(
        site.openapi.request(
            method="get",
            url="domain-types/internal/actions/discover-receiver/invoke",
        ).text
    )


@pytest.fixture(scope="session", name="relay_url")
def relay_url_fixture(site: Site, agent_receiver_port: int) -> str:
    return f"https://{site.http_address}:{agent_receiver_port}/{site.id}/relays"


@pytest.fixture(scope="module", name="relay_keypair_factory")
def relay_keypair_factory_fixture(
    site: Site,
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[str], KeyPairInfo]:
    pem_bytes = site.read_file("etc/ssl/relays/ca.pem").encode("utf-8")
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

    def _create_keypair(uuid_str: str) -> KeyPairInfo:
        private_key, csr = generate_csr_pair(uuid_str)

        private_key_path = tmp_path_factory.mktemp("relay_certs") / "private_key.key"
        with private_key_path.open("wb") as private_key_file:
            private_key_file.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        public_key_path = tmp_path_factory.mktemp("relay_certs") / "public.pem"
        with public_key_path.open("w") as public_key_file:
            public_key_file.write(
                serialize_to_pem(sign_csr(csr, 12, (root_cert, root_key), current_time_naive()))
            )

        return KeyPairInfo(
            uuid_=uuid_str,
            private_key_path=private_key_path,
            public_key_path=public_key_path,
            csr_pem=serialize_to_pem(csr),
        )

    return _create_keypair


def _register_relay(site: Site, keypair: KeyPairInfo) -> None:
    """Register a relay via the agent-receiver."""
    site.openapi_agent_receiver.relays.register(
        relay_id=keypair.uuid_,
        alias=f"relay-{keypair.uuid_}",
        csr=keypair.csr_pem,
    )


def _remove_relay(site: Site, relay_id: str) -> None:
    """Remove a relay via the site API."""
    original_api_version = site.openapi.api_version
    site.openapi.api_version = "unstable"
    try:
        site.openapi.relays.delete(relay_id=relay_id, etag="*")
    finally:
        site.openapi.api_version = original_api_version


@pytest.mark.medium_test_chain
@pytest.mark.skip_if_not_edition("ultimate", "ultimatemt", "cloud")
def test_get_relay_status_cert_mismatch(
    site: Site,
    relay_url: str,
    relay_keypair_factory: Callable[[str], KeyPairInfo],
) -> None:
    """Verify that get-relay-status rejects requests where the client certificate
    does not match the requested relay.

    Test steps:
    1. Register Relay A and Relay B (no activate-config, so no config folders)
    2. Remove Relay B via the site API
       - Relay B: valid certificate exists, but no longer in site/API/config
       - Relay A: valid certificate exists, stored in API only (no config files)
    3. GET /{relay_A}/status with Relay B's cert -> rejected (mTLS mismatch)
    4. GET /{relay_B}/status with Relay A's cert -> rejected (mTLS mismatch)
    5. GET /{relay_C}/status with Relay A's cert -> rejected (mTLS mismatch)

    Steps 3-5 are tested through real mTLS -- the worker extracts the cert CN
    and the mtls_authorization_dependency rejects the mismatch.
    """
    keypair_a = relay_keypair_factory(str(uuid.uuid4()))
    keypair_b = relay_keypair_factory(str(uuid.uuid4()))
    relay_id_c = str(uuid.uuid4())

    _register_relay(site, keypair_a)
    _register_relay(site, keypair_b)
    _remove_relay(site, keypair_b.uuid_)

    # GET /relay_A/status with Relay B's certificate -> mTLS mismatch
    resp = requests.get(
        f"{relay_url}/{keypair_a.uuid_}/status",
        cert=keypair_b.cert_tuple(),
        verify=False,
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert "does not match UUID in URL" in resp.json()["detail"]

    # GET /relay_B/status with Relay A's certificate -> mTLS mismatch
    resp = requests.get(
        f"{relay_url}/{keypair_b.uuid_}/status",
        cert=keypair_a.cert_tuple(),
        verify=False,
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN

    # GET /relay_C/status with Relay A's certificate -> mTLS mismatch
    resp = requests.get(
        f"{relay_url}/{relay_id_c}/status",
        cert=keypair_a.cert_tuple(),
        verify=False,
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.medium_test_chain
@pytest.mark.skip_if_not_edition("ultimate", "ultimatemt", "cloud")
def test_get_relay_status_activated_config_cert_mismatch(
    site: Site,
    relay_url: str,
    relay_keypair_factory: Callable[[str], KeyPairInfo],
) -> None:
    """Verify that get-relay-status rejects mTLS mismatches regardless of
    config activation state.

    Test steps:
    1. Register Relay A and Relay B (no activate-config)
    2. Remove Relay B via the site API
    3. Activate changes (creates config folder for Relay A only)
       - Relay B: valid certificate exists, but no longer in site/API/config
       - Relay A: valid certificate exists, stored in both API and config files
    4. GET /{relay_A}/status with Relay B's cert -> rejected (mTLS mismatch)
    5. GET /{relay_B}/status with Relay A's cert -> rejected (mTLS mismatch)
    6. GET /{relay_C}/status with Relay A's cert -> rejected (mTLS mismatch)

    The mTLS auth check runs before the handler, so the activation state
    does not affect the 403 rejection. Same assertions as
    test_get_relay_status_cert_mismatch.
    """
    keypair_a = relay_keypair_factory(str(uuid.uuid4()))
    keypair_b = relay_keypair_factory(str(uuid.uuid4()))
    relay_id_c = str(uuid.uuid4())

    _register_relay(site, keypair_a)
    _register_relay(site, keypair_b)
    _remove_relay(site, keypair_b.uuid_)
    site.openapi.changes.activate_and_wait_for_completion()

    # Same 3 mismatch assertions
    resp = requests.get(
        f"{relay_url}/{keypair_a.uuid_}/status",
        cert=keypair_b.cert_tuple(),
        verify=False,
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN

    resp = requests.get(
        f"{relay_url}/{keypair_b.uuid_}/status",
        cert=keypair_a.cert_tuple(),
        verify=False,
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN

    resp = requests.get(
        f"{relay_url}/{relay_id_c}/status",
        cert=keypair_a.cert_tuple(),
        verify=False,
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.medium_test_chain
@pytest.mark.skip_if_not_edition("ultimate", "ultimatemt", "cloud")
@pytest.mark.parametrize("use_registered", [True, False], ids=["registered", "unknown"])
def test_get_relay_auth(
    site: Site,
    relay_url: str,
    relay_keypair_factory: Callable[[str], KeyPairInfo],
    use_registered: bool,
) -> None:
    """Verify that get-relay-status rejects requests without proper mTLS.

    Test steps:
    1. Register only Relay A
    2. GET /{relay_id} via HTTPS without mTLS (no client cert) -> rejected
    3. GET /{relay_id} via mTLS with untrusted certificate -> rejected

    Parametrized over a relay with a valid keypair (registered) and an
    unknown relay_id (no keypair generated).
    """
    keypair_a = relay_keypair_factory(str(uuid.uuid4()))
    relay_id_b = str(uuid.uuid4())
    relay_id = keypair_a.uuid_ if use_registered else relay_id_b

    _register_relay(site, keypair_a)

    # No client certificate -- worker injects sentinel
    resp = requests.get(
        f"{relay_url}/{relay_id}/status",
        verify=False,
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert "missing: no client certificate provided" in resp.json()["detail"]

    # Spoofed header: Client sends verified-uuid header but no cert.
    # Worker prepends sentinel; FastAPI reads sentinel first -> 403.
    resp = requests.get(
        f"{relay_url}/{relay_id}/status",
        headers={"verified-uuid": relay_id},
        verify=False,
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert "missing: no client certificate provided" in resp.json()["detail"]

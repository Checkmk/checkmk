#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from base64 import urlsafe_b64encode
from pathlib import Path
from time import time

import pytest
from agent_receiver.certificates import (
    _decode_base64_cert,
    _validate_certificate,
    CertificateValidationError,
)
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509 import Certificate
from pytest_mock import MockerFixture

from tests.testlib import on_time

from omdlib.certs import CertificateAuthority


@pytest.fixture(name="ca")
def fixture_ca(
    mocker: MockerFixture,
    tmp_path: Path,
) -> CertificateAuthority:
    ca = CertificateAuthority(tmp_path / "ca", "test-ca")
    ca.initialize()
    mocker.patch(
        "agent_receiver.certificates.ROOT_CERT",
        ca._root_cert_path,
    )
    return ca


@pytest.fixture(name="trusted_cert")
def fixture_trusted_cert(ca: CertificateAuthority) -> Certificate:
    cert, _priv_key = ca._certificate_from_root("abc123")
    return cert


@pytest.fixture(name="trusted_cert_b64")
def fixture_trusted_cert_b64(trusted_cert: Certificate) -> str:
    return urlsafe_b64encode(trusted_cert.public_bytes(Encoding.DER)).decode()


@pytest.fixture(name="untrusted_cert")
def fixture_untrusted_cert(tmp_path: Path) -> Certificate:
    ca2 = CertificateAuthority(tmp_path / "ca-2", "test-ca-2")
    ca2.initialize()
    cert, _priv_key = ca2._certificate_from_root("abc123")
    return cert


@pytest.fixture(name="untrusted_cert_b64")
def fixture_untrusted_cert_b64(untrusted_cert: Certificate) -> str:
    return urlsafe_b64encode(untrusted_cert.public_bytes(Encoding.DER)).decode()


def test_decode_base64_cert_b64_invalid() -> None:
    with pytest.raises(
        ValueError,
        match="Client certificate deserialization: base64 decoding failed",
    ):
        _decode_base64_cert("asgasdg")


def test_decode_base64_cert_der_invalid() -> None:
    with pytest.raises(ValueError):
        _decode_base64_cert("bm90IGEgdmFsaWQgY2VydA==")


def test_decode_base64_cert_ok(
    trusted_cert_b64: str,
    trusted_cert: Certificate,
) -> None:
    assert _decode_base64_cert(trusted_cert_b64).public_bytes(
        Encoding.DER
    ) == trusted_cert.public_bytes(Encoding.DER)


@pytest.mark.usefixtures("ca")
def test_validate_certificate_invalid_signature(untrusted_cert: Certificate) -> None:
    with pytest.raises(
        CertificateValidationError,
        match="Client certificate not trusted",
    ):
        _validate_certificate(untrusted_cert)


def test_validate_certificate_expired(ca: CertificateAuthority) -> None:
    ca._days_valid = 1
    with on_time(1638174087, "UTC"):
        cert, _priv_key = ca._certificate_from_root("abc123")
    with pytest.raises(
        CertificateValidationError,
        match="Client certificate expired",
    ):
        _validate_certificate(cert)


def test_validate_certificate_not_yet_valid(ca: CertificateAuthority) -> None:
    with on_time(time() + 24 * 3600, "UTC"):
        cert, _priv_key = ca._certificate_from_root("abc123")
    with pytest.raises(
        CertificateValidationError,
        match="Client certificate not yet valid",
    ):
        _validate_certificate(cert)


def test_validate_certificate_ok(trusted_cert: Certificate) -> None:
    _validate_certificate(trusted_cert)

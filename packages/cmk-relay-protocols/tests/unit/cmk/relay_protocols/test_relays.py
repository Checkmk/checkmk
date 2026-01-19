#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from cmk.relay_protocols import relays


def _generate_valid_test_csr() -> str:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
        .sign(private_key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.PEM).decode()


def test_valid_csr_registration() -> None:
    csr = _generate_valid_test_csr()
    request = relays.RelayRegistrationRequest(relay_id="test", alias="bar", csr=csr)
    assert request.csr == csr


def test_valid_csr_rotation() -> None:
    csr = _generate_valid_test_csr()
    request = relays.RelayRefreshCertRequest(csr=csr)
    assert request.csr == csr


def test_invalid_csr_registration() -> None:
    with pytest.raises(ValueError):
        relays.RelayRegistrationRequest(relay_id="test", alias="bar", csr="foo")


def test_invalid_csr_rotation() -> None:
    with pytest.raises(ValueError):
        relays.RelayRefreshCertRequest(csr="foo")

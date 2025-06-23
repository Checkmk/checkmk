#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for Certificate Signing Requests"""

from uuid import UUID

import pytest
import time_machine
from dateutil.relativedelta import relativedelta

from cmk.ccc.site import SiteId

from cmk.crypto.certificate import (
    CertificateSigningRequest,
    CertificateWithPrivateKey,
)
from cmk.crypto.keys import PrivateKey
from cmk.crypto.x509 import (
    SAN,
    SubjectAlternativeNames,
    X509Name,
)


@pytest.mark.parametrize(
    "signing_cert_fixture,subject_key_fixture",
    [
        # this tries various kinds of certs/keys both as CA and as CSR subject
        ("self_signed_cert", "self_signed_ec_cert"),
        ("self_signed_ec_cert", "self_signed_ed25519_cert"),
        ("self_signed_ed25519_cert", "self_signed_cert"),
    ],
)
def test_sign_csr(
    signing_cert_fixture: str,
    subject_key_fixture: str,
    request: pytest.FixtureRequest,
) -> None:
    signing_certificate = request.getfixturevalue(signing_cert_fixture)
    # re-use the keys from our self-signed certs for convenience
    subject_key = request.getfixturevalue(subject_key_fixture).private_key

    csr = CertificateSigningRequest.create(
        subject_name=X509Name.create(common_name="csr_test", organization_name="csr_test_org"),
        subject_private_key=subject_key,
    )

    with time_machine.travel(signing_certificate.certificate.not_valid_before):
        new_cert = signing_certificate.sign_csr(csr, expiry=relativedelta(days=1))

    assert new_cert.not_valid_before == signing_certificate.certificate.not_valid_before
    assert (
        new_cert.not_valid_after
        == signing_certificate.certificate.not_valid_before + relativedelta(days=1)
    )

    new_cert.verify_is_signed_by(signing_certificate.certificate)
    assert new_cert.public_key == subject_key.public_key, (
        "The public key in the certificate matches the private key in the CSR"
    )
    assert new_cert.issuer == signing_certificate.certificate.subject, (
        "The issuer of the new certificate is the self_signed_cert"
    )


def test_csr_serialization() -> None:
    private_key = PrivateKey.generate_elliptic_curve()
    csr = CertificateSigningRequest.create(
        subject_name=X509Name.create(
            common_name="test_csr_serialization", organization_name="cmk.crypto.unittest"
        ),
        subject_private_key=private_key,
    )

    csr_pem = csr.dump_pem()
    loaded_csr = CertificateSigningRequest.load_pem(csr_pem)

    assert loaded_csr.subject == csr.subject
    assert loaded_csr.public_key == csr.public_key


def test_subject_alternative_names(
    self_signed_cert: CertificateWithPrivateKey,
    self_signed_ec_cert: CertificateWithPrivateKey,
) -> None:
    """test setting subject alt names either from the CSR or overriding it"""
    subject_key = self_signed_ec_cert.private_key

    csr_sans = SubjectAlternativeNames(
        [
            SAN.dns_name("test.example.com"),
            SAN.checkmk_site(SiteId("test_site")),
        ]
    )
    csr = CertificateSigningRequest.create(
        subject_name=X509Name.create(common_name="csr_test", organization_name="csr_test_org"),
        subject_private_key=subject_key,
        subject_alternative_names=csr_sans,
    )

    cert1 = self_signed_cert.sign_csr(csr, expiry=relativedelta(days=1))
    assert cert1.subject_alternative_names == csr_sans

    override_sans = SubjectAlternativeNames(
        [SAN.uuid(UUID("12345678-1234-5678-1234-567812345678"))]
    )
    cert2 = self_signed_cert.sign_csr(
        csr, expiry=relativedelta(days=1), subject_alternative_names=override_sans
    )
    assert cert2.subject_alternative_names == override_sans

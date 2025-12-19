#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.x509 import (
    CertificateBuilder,
    Name,
    NameAttribute,
    random_serial_number,
)
from cryptography.x509.oid import NameOID

from cmk.agent_receiver.lib.certs import (
    agent_root_ca,
    current_time_naive,
    get_local_site_cn,
    serialize_to_pem,
    sign_csr,
)
from cmk.agent_receiver.lib.config import get_config
from cmk.testlib.agent_receiver.certs import (
    check_certificate_against_private_key,
    check_certificate_against_public_key,
    check_cn,
    generate_csr_pair,
    generate_private_key,
)


def test_sign_csr() -> None:
    root_ca = agent_root_ca()
    key, csr = generate_csr_pair("peter")
    cert = sign_csr(csr, 12, root_ca, datetime.datetime.fromtimestamp(100, tz=datetime.UTC))

    assert check_cn(cert, "peter")
    assert str(cert.not_valid_before_utc) == "1970-01-01 00:01:40+00:00"
    assert str(cert.not_valid_after_utc) == "1971-01-01 00:01:40+00:00"
    check_certificate_against_private_key(
        cert,
        key,
    )
    assert isinstance(public_key := root_ca[0].public_key(), RSAPublicKey)
    check_certificate_against_public_key(cert, public_key)


def test_get_local_site_cn_custom_certificate() -> None:
    """Test get_local_site_cn with a custom certificate."""
    # Clear cache before test
    get_local_site_cn.cache_clear()

    # Create a custom certificate with a specific CN
    custom_cn = "test-site-123"
    private_key = generate_private_key(2048)
    now = current_time_naive()

    cert = (
        CertificateBuilder()
        .subject_name(
            Name(
                [
                    NameAttribute(NameOID.COMMON_NAME, custom_cn),
                ]
            )
        )
        .issuer_name(
            Name(
                [
                    NameAttribute(NameOID.COMMON_NAME, custom_cn),
                ]
            )
        )
        .public_key(private_key.public_key())
        .serial_number(random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(private_key, SHA256())
    )

    # Write the custom certificate to the site CA path
    config = get_config()
    config.site_ca_path.write_text(serialize_to_pem(cert))

    # Now get_local_site_cn should return our custom CN
    cn = get_local_site_cn()
    assert cn == custom_cn


def test_get_local_site_cn_missing_cn() -> None:
    """Test get_local_site_cn raises ValueError when certificate has no CN."""
    # Clear cache before test
    get_local_site_cn.cache_clear()

    # Create a certificate without a CN
    private_key = generate_private_key(2048)
    now = current_time_naive()

    cert = (
        CertificateBuilder()
        .subject_name(
            Name(
                [
                    NameAttribute(NameOID.COUNTRY_NAME, "DE"),
                ]
            )
        )
        .issuer_name(
            Name(
                [
                    NameAttribute(NameOID.COUNTRY_NAME, "DE"),
                ]
            )
        )
        .public_key(private_key.public_key())
        .serial_number(random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(private_key, SHA256())
    )

    # Write the certificate without CN to the site CA path
    config = get_config()
    config.site_ca_path.write_text(serialize_to_pem(cert))

    # get_local_site_cn should raise ValueError
    with pytest.raises(ValueError, match="Site certificate does not contain a Common Name"):
        get_local_site_cn()

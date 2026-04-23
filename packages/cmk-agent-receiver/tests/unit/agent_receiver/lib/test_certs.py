#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from datetime import UTC

import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509 import CertificateBuilder, Name, NameAttribute, random_serial_number
from cryptography.x509.oid import NameOID
from dateutil.relativedelta import relativedelta

from cmk.agent_receiver.lib.certs import (
    agent_root_ca,
    get_local_site_cn,
    sign_csr,
)
from cmk.agent_receiver.lib.config import get_config
from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.crypto.keys import PrivateKey, PublicKey
from cmk.testlib.agent_receiver.certs import (
    generate_csr_pair,
)


def test_sign_csr() -> None:
    root_ca = agent_root_ca()
    key, csr = generate_csr_pair("peter")
    before = datetime.datetime.now(tz=UTC).replace(microsecond=0)
    cert = sign_csr(csr, 12, root_ca)

    assert cert.subject.common_name == "peter"
    assert before <= cert.not_valid_before <= datetime.datetime.now(tz=UTC)
    assert cert.not_valid_after == cert.not_valid_before + relativedelta(months=12)
    assert cert.public_key == key.public_key
    assert isinstance(public_key := root_ca.certificate.public_key, PublicKey)
    assert isinstance(public_key.key, RSAPublicKey)
    cert.verify_is_signed_by(root_ca.certificate)


def test_get_local_site_cn_custom_certificate() -> None:
    """Test get_local_site_cn with a custom certificate."""
    # Clear cache before test
    get_local_site_cn.cache_clear()

    # Create a custom certificate with a specific CN
    custom_cn = "test-site-123"
    cert = CertificateWithPrivateKey.generate_self_signed(
        common_name=custom_cn,
        organization="Checkmk Site test-site-123",
        expiry=relativedelta(days=365),
        key_size=1024,
    )

    # Write the custom certificate to the site cert path
    config = get_config()
    config.site_cert_path.parent.mkdir(parents=True, exist_ok=True)
    config.site_cert_path.write_bytes(cert.certificate.dump_pem().bytes)

    # Now get_local_site_cn should return our custom CN
    cn = get_local_site_cn()
    assert cn == custom_cn


def test_get_local_site_cn_missing_cn() -> None:
    """Test get_local_site_cn raises ValueError when certificate has no CN."""
    # Clear cache before test
    get_local_site_cn.cache_clear()

    private_key = PrivateKey.generate_rsa(key_size=1024)
    now = datetime.datetime.now(tz=UTC)
    cert = (
        CertificateBuilder()
        .subject_name(Name([NameAttribute(NameOID.COUNTRY_NAME, "DE")]))
        .issuer_name(Name([NameAttribute(NameOID.COUNTRY_NAME, "DE")]))
        .public_key(private_key.key.public_key())
        .serial_number(random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(private_key.key, SHA256())
    )
    assert cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME) == []

    # Write the certificate without CN to the site cert path
    config = get_config()
    config.site_cert_path.parent.mkdir(parents=True, exist_ok=True)
    config.site_cert_path.write_bytes(cert.public_bytes(Encoding.PEM))

    # get_local_site_cn should raise ValueError
    with pytest.raises(ValueError, match="Site certificate does not contain a Common Name"):
        get_local_site_cn()

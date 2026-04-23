#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
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
from cmk.testlib.agent_receiver.certs import generate_csr_pair


def test_sign_csr() -> None:
    root_ca = agent_root_ca()
    key, csr = generate_csr_pair("peter")
    valid_from = datetime.datetime.fromtimestamp(100).replace(tzinfo=None)
    cert = sign_csr(csr.csr, 12, root_ca, valid_from)

    cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    assert cn_attrs[0].value == "peter"

    # Verify the cert public key matches the private key
    cert_pub = cert.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    key_pub = key.key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    assert cert_pub == key_pub


def test_get_local_site_cn_custom_certificate() -> None:
    get_local_site_cn.cache_clear()

    custom_cn = "test-site-123"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = current_time_naive()

    cert = (
        CertificateBuilder()
        .subject_name(Name([NameAttribute(NameOID.COMMON_NAME, custom_cn)]))
        .issuer_name(Name([NameAttribute(NameOID.COMMON_NAME, custom_cn)]))
        .public_key(private_key.public_key())
        .serial_number(random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(private_key, SHA256())
    )

    config = get_config()
    config.site_cert_path.parent.mkdir(parents=True, exist_ok=True)
    config.site_cert_path.write_text(serialize_to_pem(cert))

    cn = get_local_site_cn()
    assert cn == custom_cn


def test_get_local_site_cn_missing_cn() -> None:
    get_local_site_cn.cache_clear()

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = current_time_naive()

    cert = (
        CertificateBuilder()
        .subject_name(Name([NameAttribute(NameOID.COUNTRY_NAME, "DE")]))
        .issuer_name(Name([NameAttribute(NameOID.COUNTRY_NAME, "DE")]))
        .public_key(private_key.public_key())
        .serial_number(random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(private_key, SHA256())
    )

    config = get_config()
    config.site_cert_path.parent.mkdir(parents=True, exist_ok=True)
    config.site_cert_path.write_text(serialize_to_pem(cert))

    with pytest.raises(ValueError, match="Site certificate does not contain a Common Name"):
        get_local_site_cn()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path
from stat import S_IMODE

import pytest

from tests.testlib.certs import (
    check_certificate_against_private_key,
    check_certificate_against_public_key,
    check_cn,
)

import omdlib.certs as certs

from cmk.utils.certs import (
    _rsa_public_key_from_cert_or_csr,
    load_cert_and_private_key,
    root_cert_path,
    RootCA,
)

CA_NAME = "test-ca"


@pytest.fixture(name="ca")
def fixture_ca(tmp_path: Path) -> certs.CertificateAuthority:
    ca_path = tmp_path / "ca"
    return certs.CertificateAuthority(
        root_ca=RootCA(root_cert_path(ca_path), CA_NAME),
        ca_path=ca_path,
    )


def test_initialize(ca: certs.CertificateAuthority) -> None:
    assert check_cn(
        ca.root_ca.cert,
        CA_NAME,
    )
    check_certificate_against_private_key(
        ca.root_ca.cert,
        ca.root_ca.rsa,
    )


def _file_permissions_is_660(path: Path) -> bool:
    return oct(S_IMODE(path.stat().st_mode)) == "0o660"


def test_create_site_certificate(ca: certs.CertificateAuthority) -> None:
    site_id = "xyz"
    assert not ca.site_certificate_exists(site_id)

    ca.create_site_certificate(site_id)
    assert ca.site_certificate_exists(site_id)
    assert _file_permissions_is_660(ca._site_certificate_path(site_id))

    cert, key = load_cert_and_private_key(ca._site_certificate_path(site_id))
    assert check_cn(
        cert,
        site_id,
    )
    check_certificate_against_private_key(
        cert,
        key,
    )
    check_certificate_against_public_key(
        cert,
        _rsa_public_key_from_cert_or_csr(ca.root_ca.cert),
    )


def test_write_agent_receiver_certificate(ca: certs.CertificateAuthority) -> None:
    assert not ca.agent_receiver_certificate_exists

    ca.create_agent_receiver_certificate()
    assert ca.agent_receiver_certificate_exists
    assert _file_permissions_is_660(ca._agent_receiver_cert_path)

    cert, key = load_cert_and_private_key(ca._agent_receiver_cert_path)
    assert check_cn(
        cert,
        "localhost",
    )
    check_certificate_against_private_key(
        cert,
        key,
    )
    check_certificate_against_public_key(
        cert,
        _rsa_public_key_from_cert_or_csr(ca.root_ca.cert),
    )

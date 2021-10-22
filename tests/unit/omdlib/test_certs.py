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

from cmk.utils.certs import load_cert_and_private_key, rsa_public_key_from_cert_or_csr

CA_NAME = "test-ca"


@pytest.fixture(name="ca")
def fixture_ca(tmp_path: Path) -> certs.CertificateAuthority:
    return certs.CertificateAuthority(
        tmp_path / "ca",
        CA_NAME,
    )


def test_initialize(ca: certs.CertificateAuthority) -> None:
    assert not ca.is_initialized
    ca.initialize()
    assert ca.is_initialized

    cert, key = ca._get_root_certificate()
    assert check_cn(
        cert,
        CA_NAME,
    )
    check_certificate_against_private_key(
        cert,
        key,
    )


def test_create_certificates_ca_not_initialized(ca: certs.CertificateAuthority) -> None:
    with pytest.raises(RuntimeError, match="Certificate authority is not initialized yet"):
        ca.create_site_certificate("xyz")
    with pytest.raises(RuntimeError, match="Certificate authority is not initialized yet"):
        ca.create_marcv_certificate()


def _file_permissions_is_660(path: Path) -> bool:
    return oct(S_IMODE(path.stat().st_mode)) == "0o660"


def test_create_site_certificate(ca: certs.CertificateAuthority) -> None:
    ca.initialize()
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
        rsa_public_key_from_cert_or_csr(ca._get_root_certificate()[0]),
    )


def test_write_marcv_certificate(ca: certs.CertificateAuthority) -> None:
    ca.initialize()
    assert not ca.marcv_certificate_exists

    ca.create_marcv_certificate()
    assert ca.marcv_certificate_exists
    assert _file_permissions_is_660(ca._marcv_cert_path)

    cert, key = load_cert_and_private_key(ca._marcv_cert_path)
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
        rsa_public_key_from_cert_or_csr(ca._get_root_certificate()[0]),
    )

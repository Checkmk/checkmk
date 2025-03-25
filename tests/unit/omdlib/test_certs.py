#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path
from stat import S_IMODE

import pytest

from omdlib.certs import CertificateAuthority

from cmk.utils.certs import root_cert_path, RootCA

from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.crypto.keys import PlaintextPrivateKeyPEM, PrivateKey

CA_NAME = "test-ca"


@pytest.fixture(name="ca")
def fixture_ca(tmp_path: Path) -> CertificateAuthority:
    ca_path = tmp_path / "ca"
    return CertificateAuthority(
        root_ca=RootCA.load_or_create(root_cert_path(ca_path), CA_NAME),
        ca_path=ca_path,
    )


def test_initialize(ca: CertificateAuthority) -> None:
    assert ca.root_ca.certificate.common_name == CA_NAME
    assert ca.root_ca.certificate.public_key == ca.root_ca.private_key.public_key


def _file_permissions_is_660(path: Path) -> bool:
    return oct(S_IMODE(path.stat().st_mode)) == "0o660"


def test_create_site_certificate(ca: CertificateAuthority) -> None:
    site_id = "xyz"
    assert not ca.site_certificate_exists(site_id)

    ca.create_site_certificate(site_id, key_size=1024)
    assert ca.site_certificate_exists(site_id)
    assert _file_permissions_is_660(ca._site_certificate_path(site_id))

    mixed_pem = ca._site_certificate_path(site_id).read_bytes()
    certificate = Certificate.load_pem(CertificatePEM(mixed_pem))
    private_key = PrivateKey.load_pem(PlaintextPrivateKeyPEM(mixed_pem), None)

    assert certificate.common_name == site_id
    assert certificate.public_key == private_key.public_key
    certificate.verify_is_signed_by(ca.root_ca.certificate)

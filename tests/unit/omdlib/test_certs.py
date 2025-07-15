#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path
from stat import S_IMODE

import pytest

from cmk.utils.certs import SiteCA

from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.crypto.keys import PlaintextPrivateKeyPEM, PrivateKey

SITE_ID = "test-site"


@pytest.fixture(name="ca")
def fixture_ca(tmp_path: Path) -> SiteCA:
    ca_path = tmp_path / "ca"
    return SiteCA.load_or_create(
        site_id=SITE_ID,
        certificate_directory=ca_path,
        key_size=1024,
    )


def test_initialize(ca: SiteCA) -> None:
    assert ca.root_ca.certificate.common_name == f"Site '{SITE_ID}' local CA"
    assert ca.root_ca.certificate.public_key == ca.root_ca.private_key.public_key


def _file_permissions_is_660(path: Path) -> bool:
    return oct(S_IMODE(path.stat().st_mode)) == "0o660"


def test_create_site_certificate(ca: SiteCA) -> None:
    assert not ca.site_certificate_exists(SITE_ID)

    ca.create_site_certificate(SITE_ID, key_size=1024)
    assert ca.site_certificate_exists(SITE_ID)
    assert _file_permissions_is_660(ca._site_certificate_path(SITE_ID))

    mixed_pem = ca._site_certificate_path(SITE_ID).read_bytes()
    certificate = Certificate.load_pem(CertificatePEM(mixed_pem))
    private_key = PrivateKey.load_pem(PlaintextPrivateKeyPEM(mixed_pem), None)

    assert certificate.common_name == SITE_ID
    assert certificate.public_key == private_key.public_key
    certificate.verify_is_signed_by(ca.root_ca.certificate)

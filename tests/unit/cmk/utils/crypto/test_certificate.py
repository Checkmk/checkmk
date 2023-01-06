#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import AbstractContextManager
from contextlib import nullcontext as does_not_raise
from datetime import datetime
from pathlib import Path

import pytest
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from cmk.utils.crypto import Password
from cmk.utils.crypto.certificate import (
    CertificateWithPrivateKey,
    InvalidExpiryError,
    PersistedCertificateWithPrivateKey,
    RsaPrivateKey,
)

FROZEN_NOW = datetime(2023, 1, 1, 8, 0, 0)


@pytest.fixture(name="self_signed_cert", scope="module")
def fixture_self_signed() -> CertificateWithPrivateKey:
    """
    Return a self-signed certificate.

    Valid from 2023-01-01 08:00:00 til 2023-01-01 10:00:00.
    """
    with freeze_time(FROZEN_NOW):
        return CertificateWithPrivateKey.generate_self_signed(
            common_name="TestGenerateSelfSigned",
            organization="Checkmk-Unit-Tests",
            expiry=relativedelta(hours=2),
            key_size=1024,
        )


def test_generate_self_signed(self_signed_cert: CertificateWithPrivateKey) -> None:
    assert (
        self_signed_cert.public_key
        == self_signed_cert.certificate.public_key
        == self_signed_cert.private_key.public_key
    )
    self_signed_cert.certificate.verify_is_signed_by(self_signed_cert.certificate)


@pytest.mark.parametrize(
    "time_offset,allowed_drift,expectation",
    [
        (
            relativedelta(hours=-5),  # It's 5 hours BEFORE cert creation.
            None,  # The default 2 hours slack is not enough.
            pytest.raises(InvalidExpiryError, match="not yet valid"),
        ),
        (relativedelta(hours=5), None, pytest.raises(InvalidExpiryError, match="expired")),
        (
            relativedelta(hours=5),  # It's now 5 hours after cert creation, so the cert has expired
            # 3 hours ago.
            relativedelta(hours=5),  # But we allow 5 hours drift.
            does_not_raise(),
        ),
        (relativedelta(minutes=10), None, does_not_raise()),
    ],
)
def test_verify_expiry(
    self_signed_cert: CertificateWithPrivateKey,
    time_offset: relativedelta,
    allowed_drift: relativedelta,
    expectation: AbstractContextManager,
) -> None:
    # time_offset is the time difference to (mocked) certificate creation
    # allowed_drift is the tolerance parameter of verify_expiry (defaults to 2 hours for None)
    #
    # We assume the cert is valid from FROZEN_NOW til FROZEN_NOW + 2 hours.
    #
    with freeze_time(FROZEN_NOW + time_offset):
        with expectation:
            self_signed_cert.certificate.verify_expiry(allowed_drift)


def test_write_and_read(tmp_path: Path, self_signed_cert: CertificateWithPrivateKey) -> None:
    cert_path = tmp_path / "cert.crt"
    key_path = tmp_path / "key.pem"
    password = Password("geheim")

    _persisted = PersistedCertificateWithPrivateKey.persist(
        self_signed_cert, cert_path, key_path, password
    )

    assert key_path.read_bytes().splitlines()[0] == b"-----BEGIN ENCRYPTED PRIVATE KEY-----"
    assert cert_path.read_bytes().splitlines()[0] == b"-----BEGIN CERTIFICATE-----"

    loaded = PersistedCertificateWithPrivateKey.read_files(cert_path, key_path, password)

    assert (
        loaded.certificate._cert.serial_number == self_signed_cert.certificate._cert.serial_number
    )
    # mypy doesn't find most attributes of cryptography's RSAPrivateKey as it seems
    loaded_nums = loaded.private_key._key.private_numbers()  # type: ignore[attr-defined]
    orig_nums = self_signed_cert.private_key._key.private_numbers()  # type: ignore[attr-defined]
    assert loaded_nums == orig_nums


def test_serialize_rsa_key(tmp_path: Path) -> None:
    key = RsaPrivateKey.generate(512)

    pem_plain = key.dump_pem(None)
    assert pem_plain.startswith(b"-----BEGIN PRIVATE KEY-----")

    loaded_plain = RsaPrivateKey.load_pem(pem_plain)
    assert loaded_plain._key.private_numbers() == key._key.private_numbers()  # type: ignore[attr-defined]

    pem_enc = key.dump_pem(Password("verysecure"))
    assert pem_enc.startswith(b"-----BEGIN ENCRYPTED PRIVATE KEY-----")

    with pytest.raises(ValueError):
        RsaPrivateKey.load_pem(pem_enc, Password("wrong"))

    loaded_enc = RsaPrivateKey.load_pem(pem_enc, Password("verysecure"))
    assert loaded_enc._key.private_numbers() == key._key.private_numbers()  # type: ignore[attr-defined]

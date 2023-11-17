#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

import cryptography.hazmat.primitives.asymmetric as asym
import pytest
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from cmk.utils.crypto.certificate import CertificateWithPrivateKey
from cmk.utils.crypto.keys import PrivateKey


@pytest.fixture(name="self_signed_cert", scope="module")
def fixture_self_signed() -> CertificateWithPrivateKey:
    """
    Return a self-signed certificate.

    Valid from 2023-01-01 08:00:00 til 2023-01-01 10:00:00.
    """
    with freeze_time(datetime(2023, 1, 1, 8, 0, 0)):
        return CertificateWithPrivateKey.generate_self_signed(
            common_name="TestGenerateSelfSigned",
            expiry=relativedelta(hours=2),
            key_size=1024,
            is_ca=True,
        )


@pytest.fixture(name="rsa_key", scope="module")
def fixture_rsa_key() -> PrivateKey:
    return PrivateKey.generate_rsa(1024)


def rsa_private_keys_equal(key_a: PrivateKey, key_b: PrivateKey) -> bool:
    """Check if two keys are the same RSA key"""
    # Asserting key types here just to cut corners on type checking
    # (ed25519 keys don't have private_numbers())
    assert isinstance(key_a._key, asym.rsa.RSAPrivateKey) and isinstance(
        key_b._key, asym.rsa.RSAPrivateKey
    )
    return key_a._key.private_numbers() == key_b._key.private_numbers()

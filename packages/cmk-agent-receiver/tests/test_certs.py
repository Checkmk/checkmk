#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from cmk.agent_receiver.certs import agent_root_ca, sign_agent_csr

from .certs import (
    check_certificate_against_private_key,
    check_certificate_against_public_key,
    check_cn,
    generate_csr_pair,
)


def test_sign_csr() -> None:
    root_ca = agent_root_ca()
    key, csr = generate_csr_pair("peter")
    cert = sign_agent_csr(csr, 12, root_ca, datetime.datetime.fromtimestamp(100, tz=datetime.UTC))

    assert check_cn(cert, "peter")
    assert str(cert.not_valid_before_utc) == "1970-01-01 00:01:40+00:00"
    assert str(cert.not_valid_after_utc) == "1971-01-01 00:01:40+00:00"
    check_certificate_against_private_key(
        cert,
        key,
    )
    assert isinstance(public_key := root_ca[0].public_key(), RSAPublicKey)
    check_certificate_against_public_key(cert, public_key)

#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from agent_receiver.certs import agent_root_ca, sign_agent_csr
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from tests.testlib import on_time
from tests.testlib.certs import (
    check_certificate_against_private_key,
    check_certificate_against_public_key,
    check_cn,
    generate_csr_pair,
)


def test_sign_csr() -> None:
    root_ca = agent_root_ca()
    key, csr = generate_csr_pair("peter")
    with on_time(100, "UTC"):
        cert = sign_agent_csr(csr, 12, root_ca)

    assert check_cn(cert, "peter")
    assert str(cert.not_valid_before) == "1970-01-01 00:01:40"
    assert str(cert.not_valid_after) == "1971-01-01 00:01:40"
    check_certificate_against_private_key(
        cert,
        key,
    )
    assert isinstance(public_key := root_ca[0].public_key(), RSAPublicKey)
    check_certificate_against_public_key(cert, public_key)

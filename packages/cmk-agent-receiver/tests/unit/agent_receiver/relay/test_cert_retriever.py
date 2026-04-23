#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC

import pytest
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from dateutil.relativedelta import relativedelta

from cmk.agent_receiver.relay.api.routers.relays.handlers.cert_retriever import get_certificates
from cmk.agent_receiver.relay.lib.shared_types import CertificateCNError
from cmk.testlib.agent_receiver import certs as certslib
from cmk.testlib.agent_receiver.relay import random_relay_id


def test_process_creates_valid_certificate() -> None:
    relay_id = random_relay_id()
    private_key, csr = certslib.generate_csr_pair(cn=relay_id)

    certificates = get_certificates(csr.dump_pem().bytes.decode(), relay_id)

    cert = certslib.read_certificate(certificates.client_cert)
    assert cert.common_name == relay_id
    cert_pub = cert._cert.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)  # noqa: SLF001
    key_pub = private_key.key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    assert cert_pub == key_pub


def test_process_validates_csr() -> None:
    relay_id = random_relay_id()
    _, csr = certslib.generate_csr_pair(cn=random_relay_id())
    with pytest.raises(CertificateCNError, match="Unexpected certificate CN value"):
        get_certificates(csr.dump_pem().bytes.decode(), relay_id)


def test_certificate_lifetime() -> None:
    relay_id = random_relay_id()
    _, csr = certslib.generate_csr_pair(cn=relay_id)

    certificates = get_certificates(csr.dump_pem().bytes.decode(), relay_id)

    client_certificate = certslib.read_certificate(certificates.client_cert)
    now = datetime.now(tz=UTC)

    assert client_certificate.not_valid_before <= now
    assert client_certificate.not_valid_before >= now - timedelta(minutes=1)
    assert client_certificate.not_valid_after <= now + relativedelta(months=3)

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC

import pytest
from dateutil.relativedelta import relativedelta

from cmk.agent_receiver.lib.certs import serialize_to_pem
from cmk.agent_receiver.relay.api.routers.relays.handlers.cert_retriever import get_certificates
from cmk.agent_receiver.relay.lib.shared_types import CertificateCNError
from cmk.testlib.agent_receiver import certs as certslib
from cmk.testlib.agent_receiver.relay import random_relay_id


def test_process_creates_valid_certificate() -> None:
    """Verify that get_certificates creates a valid certificate with correct CN and matching keys."""
    relay_id = random_relay_id()
    private_key, csr = certslib.generate_csr_pair(cn=relay_id)

    certificates = get_certificates(serialize_to_pem(csr), relay_id)

    cert = certslib.read_certificate(certificates.client_cert)
    assert certslib.check_cn(cert, relay_id)
    certslib.check_certificate_against_private_key(cert, private_key)


def test_process_validates_csr() -> None:
    """Verify that get_certificates raises ValueError when CSR CN does not match relay ID."""
    relay_id = random_relay_id()
    _, csr = certslib.generate_csr_pair(cn=random_relay_id())
    with pytest.raises(CertificateCNError, match="Unexpected certificate CN value"):
        get_certificates(serialize_to_pem(csr), relay_id)


def test_certificate_lifetime() -> None:
    """Verify that the generated certificate has correct validity period bounds.

    The certificate should be valid starting from now and expire
    no later than 3 months from now.
    """
    relay_id = random_relay_id()
    _, csr = certslib.generate_csr_pair(cn=relay_id)

    certificates = get_certificates(serialize_to_pem(csr), relay_id)

    client_certificate = certslib.read_certificate(certificates.client_cert)
    now = datetime.now(tz=UTC)

    assert client_certificate.not_valid_before_utc <= now
    assert client_certificate.not_valid_before_utc >= now - timedelta(minutes=1)
    assert client_certificate.not_valid_after_utc <= now + relativedelta(months=3)

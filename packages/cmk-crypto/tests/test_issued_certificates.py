#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the tracking of issued certificates"""

import json
from datetime import datetime, UTC
from pathlib import Path

import time_machine
from cryptography import x509 as pyca_x509
from dateutil.relativedelta import relativedelta

from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.x509 import SAN, SubjectAlternativeNames


def test_issued_certificate_is_recorded(
    self_signed_cert: CertificateWithPrivateKey, tmp_path: Path
) -> None:
    cert_log = tmp_path / "relays-issued-certificates.jsonl"
    with time_machine.travel(datetime(2026, 9, 14, 12, 0, 0, tzinfo=UTC)):
        issued = self_signed_cert.issue_new_certificate(
            common_name="my-relay",
            organization="Checkmk Testing",
            subject_alternative_names=SubjectAlternativeNames([SAN.dns_name("my-relay")]),
            expiry=relativedelta(years=1),
            key_size=1024,
            cert_log=cert_log,
        ).certificate

    assert json.loads(cert_log.read_text()) == {
        "ts": "2026-09-14T12:00:00Z",
        "event": "issued",
        "serial": issued.serial_number_string.replace(":", ""),
        "fp_sha256": issued.fingerprint(HashAlgorithm.Sha256).hex(),
        "issuer_ski": self_signed_cert.certificate.get_extension_for_class(
            pyca_x509.SubjectKeyIdentifier
        ).value.digest.hex(),
        "subject": "O=Checkmk Testing,CN=my-relay",
        "san": {"dns": ["my-relay"]},
        "not_before": "2026-09-14T12:00:00Z",
        "not_after": "2027-09-14T12:00:00Z",
    }

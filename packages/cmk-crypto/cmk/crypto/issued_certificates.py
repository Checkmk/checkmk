#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Append-only JSON lines files keeping track of the certificates our CAs issue."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Literal, TYPE_CHECKING

from cryptography import x509 as pyca_x509

from .hash import HashAlgorithm

if TYPE_CHECKING:
    # cmk.crypto.certificate imports this module at runtime, so this import must stay type-only.
    from .certificate import Certificate  # py-import-cycles: ignore

IssuedCertificatesComponent = Literal["agents", "relays", "messaging", "sites"]


def issued_certificates_file(log_dir: Path, component: IssuedCertificatesComponent) -> Path:
    return log_dir / f"{component}-issued-certificates.jsonl"


@dataclass(frozen=True)
class IssuedCertificateEntry:
    """One line of an issued certificates file. The field names are the keys used in the file."""

    ts: str
    event: Literal["issued"]
    serial: str
    fp_sha256: str
    issuer_ski: str | None
    subject: str
    san: dict[str, list[str]]
    not_before: str
    not_after: str

    @classmethod
    def from_certificate(
        cls, certificate: Certificate, event: Literal["issued"]
    ) -> IssuedCertificateEntry:
        issuer_key_id = certificate.authority_key_identifier
        return cls(
            ts=_format_timestamp(datetime.now(tz=UTC)),
            event=event,
            serial=certificate.serial_number_string.replace(":", ""),
            fp_sha256=certificate.fingerprint(HashAlgorithm.Sha256).hex(),
            issuer_ski=None if issuer_key_id is None else issuer_key_id.hex(),
            subject=certificate.subject.rfc4514_string(),
            san={"dns": _dns_names(certificate)},
            not_before=_format_timestamp(certificate.not_valid_before),
            not_after=_format_timestamp(certificate.not_valid_after),
        )

    def append_to(self, cert_log: Path) -> None:
        cert_log.parent.mkdir(parents=True, exist_ok=True)
        with cert_log.open(mode="a", encoding="utf-8") as issued_certificates:
            issued_certificates.write(json.dumps(asdict(self)) + "\n")


def _format_timestamp(timestamp: datetime) -> str:
    return timestamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dns_names(certificate: Certificate) -> list[str]:
    try:
        sans = certificate.get_extension_for_class(pyca_x509.SubjectAlternativeName).value
    except pyca_x509.ExtensionNotFound:
        return []
    return sans.get_values_for_type(pyca_x509.DNSName)

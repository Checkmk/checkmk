#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides commonly used functions for the handling of encrypted
data within the Checkmk ecosystem."""

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from __future__ import annotations

import contextlib
import re
import socket
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

from OpenSSL import crypto, SSL

from cmk.ccc.exceptions import MKGeneralException
from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.crypto.hash import HashAlgorithm

_PEM_RE = re.compile(
    "-----BEGIN CERTIFICATE-----\r?.+?\r?-----END CERTIFICATE-----\r?\n?", re.DOTALL
)


def raw_certificates_from_file(path: Path) -> list[str]:
    try:
        # Some users use comments in certificate files e.g. to write the content of the
        # certificate outside of encapsulation boundaries. We only want to extract the
        # certificates between the encapsulation boundaries which have to be 7-bit ASCII
        # characters.
        with path.open("r", encoding="ascii", errors="surrogateescape") as f:
            return [
                content
                for match in _PEM_RE.finditer(f.read())
                if (content := match.group(0)).isascii()
            ]
    except FileNotFoundError:
        # Silently ignore e.g. dangling symlinks
        return []


class CertificateDetails(NamedTuple):
    issued_to: str
    issued_by: str
    valid_from: str
    valid_till: str
    signature_algorithm: str
    digest_sha256: str
    serial_number: int
    is_ca: bool
    verify_result: ChainVerifyResult


class ChainVerifyResult(NamedTuple):
    cert_pem: bytes
    error_number: int
    error_depth: int
    error_message: str
    is_valid: bool


# NOTE: Use this function only in conjunction with the permission server_side_requests
def fetch_certificate_details(
    trusted_ca_file: Path, address_family: socket.AddressFamily, address: tuple[str, int]
) -> Iterable[CertificateDetails]:
    """Creates a list of certificate details for the chain certs"""
    verify_chain_results = _fetch_certificate_chain_verify_results(
        trusted_ca_file, address_family, address
    )
    if not verify_chain_results:
        raise MKGeneralException("Failed to fetch the certificate chain")

    for result in verify_chain_results:
        cmk_cert = Certificate.load_pem(CertificatePEM(result.cert_pem))

        yield CertificateDetails(
            issued_to=cmk_cert.common_name or "Unknown subject name",
            issued_by=cmk_cert.issuer.common_name or "Unknown issuer name",
            valid_from=str(cmk_cert.not_valid_before),
            valid_till=str(cmk_cert.not_valid_after),
            signature_algorithm=algo.name
            if (algo := cmk_cert._cert.signature_hash_algorithm)
            else "Unknown signature algorithm",
            digest_sha256=cmk_cert.fingerprint(HashAlgorithm.Sha256).hex(),
            serial_number=cmk_cert.serial_number,
            is_ca=cmk_cert.may_sign_certificates(),
            verify_result=result,
        )


def _fetch_certificate_chain_verify_results(
    trusted_ca_file: Path,
    address_family: socket.AddressFamily,
    address: tuple[str, int],
) -> list[ChainVerifyResult]:
    """Opens a SSL connection and performs a handshake to get the certificate chain"""

    ctx = SSL.Context(SSL.SSLv23_METHOD)
    ctx.load_verify_locations(str(trusted_ca_file))

    with contextlib.closing(
        SSL.Connection(ctx, socket.socket(address_family, socket.SOCK_STREAM))
    ) as sock:
        # pylint does not get the object type of sock right
        sock.connect(address)
        sock.do_handshake()
        certificate_store = sock.get_context().get_cert_store()
        certificate_chain = sock.get_peer_cert_chain()

    # Can't verify anything without store and chain
    if certificate_store is None or not certificate_chain:
        return []

    verify_chain_results = []

    # Used to record all certificates and verification results for later displaying
    for cert in certificate_chain:
        # This is mainly done to get the textual error message without accessing internals of the SSL modules
        error_number, error_depth, error_message = 0, 0, ""
        try:
            crypto.X509StoreContext(certificate_store, cert).verify_certificate()
        except crypto.X509StoreContextError as e:
            error_number, error_depth, error_message = e.errors

        verify_chain_results.append(
            ChainVerifyResult(
                cert_pem=crypto.dump_certificate(crypto.FILETYPE_PEM, cert),
                error_number=error_number,
                error_depth=error_depth,
                error_message=error_message,
                is_valid=error_number == 0,
            )
        )

    return verify_chain_results

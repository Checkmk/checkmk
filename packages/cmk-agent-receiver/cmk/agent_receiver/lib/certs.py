#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import cache
from uuid import UUID

from dateutil.relativedelta import relativedelta

from cmk.agent_receiver.lib.config import get_config
from cmk.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateSigningRequest,
    CertificateSigningRequestPEM,
    CertificateWithPrivateKey,
)
from cmk.crypto.x509 import SAN, SubjectAlternativeNames


def site_root_certificate() -> Certificate:
    config = get_config()
    return Certificate.load_pem(CertificatePEM(config.site_ca_path.read_bytes()))


def sign_csr(
    csr: CertificateSigningRequest,
    lifetime_in_months: int,
    keypair: CertificateWithPrivateKey,
) -> Certificate:
    expiry = relativedelta(months=lifetime_in_months)
    return keypair.sign_csr(
        csr, expiry, SubjectAlternativeNames([SAN.dns_name(extract_cn_from_csr(csr))])
    )


def serialize_to_pem(certificate: Certificate | CertificateSigningRequest) -> str:
    return certificate.dump_pem().str


def extract_cn_from_csr(csr: CertificateSigningRequest) -> str:
    if csr.subject.common_name is None:
        raise ValueError("CSR contains no CN")
    return csr.subject.common_name


def validate_csr(csr: CertificateSigningRequest | str) -> CertificateSigningRequest:
    if not isinstance(csr, CertificateSigningRequest):
        csr = CertificateSigningRequest.load_pem(CertificateSigningRequestPEM(csr.encode()))

    if not csr.is_signature_valid:
        raise ValueError("Invalid CSR (signature and public key do not match)")
    cn = extract_cn_from_csr(csr)
    try:
        UUID(cn)
    except ValueError as e:
        raise ValueError(f"CN {cn} is not a valid version-4 UUID") from e

    return csr


@cache
def agent_root_ca() -> CertificateWithPrivateKey:
    config = get_config()
    content = config.agent_ca_path.read_text()
    return CertificateWithPrivateKey.load_combined_file_content(content, passphrase=None)


@cache
def relay_root_ca() -> CertificateWithPrivateKey:
    config = get_config()
    content = config.relay_ca_path.read_text()
    return CertificateWithPrivateKey.load_combined_file_content(content, passphrase=None)


@cache
def get_local_site_cn() -> str:
    """Extract the Common Name (CN) from the local site's certificate.

    This function loads the site's certificate and extracts its CN.
    The result is cached for performance since the site certificate doesn't change
    during runtime.

    Returns:
        The Common Name from the site certificate.

    Raises:
        ValueError: If the certificate doesn't contain a CN attribute.
    """
    config = get_config()
    site_cert = Certificate.load_pem(CertificatePEM(config.site_cert_path.read_bytes()))
    if site_cert.common_name is None:
        raise ValueError("Site certificate does not contain a Common Name (CN)")
    return site_cert.common_name

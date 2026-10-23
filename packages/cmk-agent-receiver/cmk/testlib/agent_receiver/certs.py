#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from datetime import datetime, UTC
from functools import cache
from ipaddress import IPv4Address
from pathlib import Path
from typing import NamedTuple

from dateutil.relativedelta import relativedelta

from cmk.agent_receiver.lib.certs import agent_root_ca, get_local_site_cn, relay_root_ca
from cmk.agent_receiver.lib.config import Config
from cmk.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateRevocationList,
    CertificateSigningRequest,
    CertificateWithPrivateKey,
    RevokedCertificate,
)
from cmk.crypto.issued_certificates import issued_certificates_file, IssuedCertificateEntry
from cmk.crypto.keys import PrivateKey
from cmk.crypto.x509 import SAN, SubjectAlternativeNames, X509Name

_CERT_EXPIRY = relativedelta(days=365)
_KEY_SIZE = 2048

# The ClientCertWorker injects the serial number of the presented certificate so that
# revoked certificates can be rejected. Clients that talk to the in-process TestClient
# present no certificate at all, so they stand in a serial number that no CA revoked.
UNREVOKED_SERIAL_NUMBER = "01"


def agent_ca_common_name(site_name: str) -> str:
    return f"Site '{site_name}' agent signing CA"


def relay_ca_common_name(site_name: str) -> str:
    return f"Site '{site_name}' relay signing CA"


class _SiteCerts(NamedTuple):
    site_ca: CertificateWithPrivateKey
    agent_ca: CertificateWithPrivateKey
    relay_ca: CertificateWithPrivateKey
    site_cert: CertificateWithPrivateKey


def set_up_site_certs(config: Config) -> None:
    """Mirror the cert layout that omd and the init.d script create at site startup.

    Writes the site, agent and relay CAs, the site certificate issued by the site CA,
    and the cert-only trust store (agent_cert_store.pem) of all three CA certs. Sites
    with the same name share the CAs and site certificate.
    """
    certs = _generate_site_certs(config.site_name)

    for ca, path in [
        (certs.site_ca, config.site_ca_path),
        (certs.agent_ca, config.agent_ca_path),
        (certs.relay_ca, config.relay_ca_path),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(ca.private_key.dump_pem(None).bytes + ca.certificate.dump_pem().bytes)

    IssuedCertificateEntry.from_certificate(certs.site_cert.certificate, "issued").append_to(
        issued_certificates_file(config.omd_root / "var/log", "sites")
    )
    config.site_cert_path.parent.mkdir(parents=True, exist_ok=True)
    config.site_cert_path.write_bytes(
        certs.site_cert.private_key.dump_pem(None).bytes
        + certs.site_cert.certificate.dump_pem().bytes
    )

    # Cert-only trust store: agents/*.pem + relays/*.pem + ca.pem (no private keys)
    cert_store = config.agent_cert_store_path
    cert_store.write_bytes(
        certs.agent_ca.certificate.dump_pem().bytes
        + certs.relay_ca.certificate.dump_pem().bytes
        + certs.site_ca.certificate.dump_pem().bytes
    )

    agent_root_ca.cache_clear()
    relay_root_ca.cache_clear()
    get_local_site_cn.cache_clear()


# Generating the four RSA keys dominates the setup time of every test using this, so
# they are generated once per process. Each site still gets its own files.
@cache
def _generate_site_certs(site_name: str) -> _SiteCerts:
    site_ca = CertificateWithPrivateKey.generate_self_signed(
        common_name=f"Site '{site_name}' local CA",
        organization=f"Checkmk Site {site_name}",
        expiry=_CERT_EXPIRY,
        key_size=_KEY_SIZE,
        is_ca=True,
    )
    return _SiteCerts(
        site_ca=site_ca,
        agent_ca=CertificateWithPrivateKey.generate_self_signed(
            common_name=agent_ca_common_name(site_name),
            organization=f"Checkmk Site {site_name}",
            expiry=_CERT_EXPIRY,
            key_size=_KEY_SIZE,
            is_ca=True,
        ),
        relay_ca=CertificateWithPrivateKey.generate_self_signed(
            common_name=relay_ca_common_name(site_name),
            organization=f"Checkmk Site {site_name}",
            expiry=_CERT_EXPIRY,
            key_size=_KEY_SIZE,
            is_ca=True,
        ),
        site_cert=site_ca.issue_new_certificate(
            common_name=site_name,
            organization=f"Checkmk Site {site_name}",
            expiry=_CERT_EXPIRY,
            key_size=_KEY_SIZE,
            subject_alternative_names=SubjectAlternativeNames(
                [SAN.ip_address(IPv4Address("127.0.0.1"))]
            ),
            # set_up_site_certs logs the issuance in each site it sets up.
            cert_log=Path(os.devnull),
        ),
    )


def revoke_serial_number(ca_path: Path, serial_number: int) -> None:
    ca = CertificateWithPrivateKey.load_combined_file_content(ca_path.read_text(), passphrase=None)
    crl = CertificateRevocationList.create(
        issuer=ca,
        revoked_certificates=[RevokedCertificate(serial_number, datetime.now(tz=UTC))],
    )
    ca_path.with_suffix(".crl").write_bytes(crl.dump_pem().bytes)


def generate_csr_pair(
    cn: str, private_key_size: int = 2048
) -> tuple[PrivateKey, CertificateSigningRequest]:
    private_key = PrivateKey.generate_rsa(key_size=private_key_size)
    return (
        private_key,
        CertificateSigningRequest.create(
            subject_name=X509Name.create(common_name=cn),
            subject_private_key=private_key,
        ),
    )


def read_certificate(pem_data: str) -> Certificate:
    return Certificate.load_pem(CertificatePEM(pem_data.encode()))

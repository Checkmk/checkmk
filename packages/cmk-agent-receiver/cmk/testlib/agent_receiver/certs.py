#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dateutil.relativedelta import relativedelta

from cmk.agent_receiver.lib.certs import agent_root_ca, get_local_site_cn, relay_root_ca
from cmk.agent_receiver.lib.config import Config
from cmk.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateSigningRequest,
    CertificateWithPrivateKey,
)
from cmk.crypto.keys import PrivateKey
from cmk.crypto.x509 import X509Name

_CERT_EXPIRY = relativedelta(days=365)
_KEY_SIZE = 2048


def set_up_site_certs(config: Config) -> None:
    """Mirror the cert layout that omd and the init.d script create at site startup.

    Three independent self-signed CAs are generated (site, agent, relay), each written
    as key+cert PEM to their canonical path. A site server certificate is issued by the
    site CA and written to etc/ssl/sites/<site>.pem. Finally, a cert-only trust store
    (agent_cert_store.pem) is assembled from the agent CA, relay CA, and site CA certs,
    matching what the init.d startup script builds via `openssl x509`.
    """
    site_ca = CertificateWithPrivateKey.generate_self_signed(
        common_name=f"Site '{config.site_name}' local CA",
        organization=f"Checkmk Site {config.site_name}",
        expiry=_CERT_EXPIRY,
        key_size=_KEY_SIZE,
        is_ca=True,
    )
    agent_ca = CertificateWithPrivateKey.generate_self_signed(
        common_name=f"Site '{config.site_name}' agent signing CA",
        organization=f"Checkmk Site {config.site_name}",
        expiry=_CERT_EXPIRY,
        key_size=_KEY_SIZE,
        is_ca=True,
    )
    relay_ca = CertificateWithPrivateKey.generate_self_signed(
        common_name=f"Site '{config.site_name}' relay signing CA",
        organization=f"Checkmk Site {config.site_name}",
        expiry=_CERT_EXPIRY,
        key_size=_KEY_SIZE,
        is_ca=True,
    )

    for ca, path in [
        (site_ca, config.site_ca_path),
        (agent_ca, config.agent_ca_path),
        (relay_ca, config.relay_ca_path),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(ca.private_key.dump_pem(None).bytes + ca.certificate.dump_pem().bytes)

    site_cert = site_ca.issue_new_certificate(
        common_name=config.site_name,
        organization=f"Checkmk Site {config.site_name}",
        expiry=_CERT_EXPIRY,
        key_size=_KEY_SIZE,
    )
    config.site_cert_path.parent.mkdir(parents=True, exist_ok=True)
    config.site_cert_path.write_bytes(
        site_cert.private_key.dump_pem(None).bytes + site_cert.certificate.dump_pem().bytes
    )

    # Cert-only trust store: agents/*.pem + relays/*.pem + ca.pem (no private keys)
    cert_store = config.omd_root / "etc/ssl/agent_cert_store.pem"
    cert_store.write_bytes(
        agent_ca.certificate.dump_pem().bytes
        + relay_ca.certificate.dump_pem().bytes
        + site_ca.certificate.dump_pem().bytes
    )

    agent_root_ca.cache_clear()
    relay_root_ca.cache_clear()
    get_local_site_cn.cache_clear()


def generate_csr_pair(
    cn: str, private_key_size: int = 1024
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

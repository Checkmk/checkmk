#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import argparse
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dateutil.relativedelta import relativedelta

import cmk.utils.paths
from cmk import messaging
from cmk.ccc.site import SiteId
from cmk.utils.certs import (
    agent_root_ca_path,
    cert_dir,
    CertManagementEvent,
    RootCA,
    SiteBrokerCA,
    SiteBrokerCertificate,
    SiteCA,
)
from cmk.utils.log.security_event import log_security_event

CertificateType = Literal["site", "site-ca", "agent-ca", "broker-ca", "broker"]


@dataclass
class Args:
    target_certificate: CertificateType
    expiry: int
    replace: bool


def _parse_args(args: Sequence[str]) -> Args:
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "target_certificate",
        choices=["site", "site-ca", "agent-ca", "broker-ca", "broker"],
        help="specify which certificate to create",
    )
    parser.add_argument(
        "--expiry",
        type=int,
        default=90,
        help="specify the expiry time in days",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        default=False,
        help="specify if the certificate currently in place has to be replaced",
    )

    parsed_args = parser.parse_args(args)

    return Args(
        target_certificate=parsed_args.target_certificate,
        expiry=parsed_args.expiry,
        replace=parsed_args.replace,
    )


def _certificate_paths(
    target_certificate: CertificateType,
    site_id: SiteId,
    omd_root: Path,
) -> list[Path]:
    match target_certificate:
        case "site":
            return [SiteCA.site_certificate_path(cert_dir=cert_dir(omd_root), site_id=site_id)]

        case "site-ca":
            return [SiteCA.root_ca_path(cert_dir=cert_dir(omd_root))]

        case "agent-ca":
            return [agent_root_ca_path(site_root_dir=omd_root)]

        case "broker-ca":
            return [
                messaging.cacert_file(omd_root),
                messaging.ca_key_file(omd_root),
                messaging.trusted_cas_file(omd_root),
            ]

        case "broker":
            return [messaging.site_cert_file(omd_root), messaging.site_key_file(omd_root)]

        case _:
            raise ValueError(f"Unknown certificate type: {target_certificate}")


def replace_site_certificate(
    site_id: SiteId,
    certificate_directory: Path,
    expiry: relativedelta,
    key_size: int = 4096,
) -> None:
    site_ca = SiteCA.load(certificate_directory=certificate_directory)

    site_ca.create_site_certificate(
        site_id=site_id,
        expiry=expiry,
        key_size=key_size,
    )

    site_cert = SiteCA.load_site_certificate(cert_dir=certificate_directory, site_id=site_id)

    log_security_event(
        CertManagementEvent(
            event="certificate rotated",
            component="site certificate",
            actor="cmk-cert",
            cert=site_cert.certificate if site_cert else None,
        )
    )


def replace_site_ca(
    site_id: SiteId,
    certificate_directory: Path,
    expiry: relativedelta,
    key_size: int = 4096,
) -> None:
    site_ca = SiteCA.create(
        cert_dir=certificate_directory,
        site_id=site_id,
        expiry=expiry,
        key_size=key_size,
    )

    log_security_event(
        CertManagementEvent(
            event="certificate rotated",
            component="site certificate authority",
            actor="cmk-cert",
            cert=site_ca.root_ca.certificate,
        )
    )


def replace_agent_ca(
    site_id: SiteId,
    omd_root: Path,
    expiry: relativedelta,
    key_size: int = 4096,
) -> None:
    agent_ca_path = agent_root_ca_path(site_root_dir=omd_root)

    root_ca = RootCA.create(
        path=agent_ca_path,
        name=f"Site '{site_id}' agent signing CA",
        validity=expiry,
        key_size=key_size,
    )

    log_security_event(
        CertManagementEvent(
            event="certificate rotated",
            component="agent certificate authority",
            actor="cmk-cert",
            cert=root_ca.certificate,
        )
    )


def replace_broker_ca(
    site_id: SiteId,
    omd_root: Path,
    expiry: relativedelta,
    key_size: int = 4096,
) -> None:
    ca = SiteBrokerCA(messaging.cacert_file(omd_root), messaging.ca_key_file(omd_root))
    ca_cert_bundle = ca.create_and_persist(site_name=site_id, expiry=expiry, key_size=key_size)

    ca.write_trusted_cas(messaging.trusted_cas_file(omd_root))

    log_security_event(
        CertManagementEvent(
            event="certificate rotated",
            component="broker certificate authority",
            actor="cmk-cert",
            cert=ca_cert_bundle.certificate,
        )
    )


def replace_broker_certificate(
    site_id: SiteId,
    omd_root: Path,
    expiry: relativedelta,
    key_size: int = 4096,
) -> None:
    ca = SiteBrokerCA(messaging.cacert_file(omd_root), messaging.ca_key_file(omd_root))
    ca_cert_bundle = ca.load()

    site_broker_cert = SiteBrokerCertificate(
        messaging.site_cert_file(omd_root), messaging.site_key_file(omd_root)
    )
    site_broker_cert_bundle = site_broker_cert.create_bundle(
        site_id, ca_cert_bundle, expiry=expiry, key_size=key_size
    )
    site_broker_cert.persist(site_broker_cert_bundle)

    log_security_event(
        CertManagementEvent(
            event="certificate rotated",
            component="broker certificate",
            actor="cmk-cert",
            cert=site_broker_cert_bundle.certificate,
        )
    )


def _cert_files_exist(
    target_certificate: CertificateType,
    site_id: SiteId,
    omd_root: Path,
) -> bool:
    target_certificate_paths = _certificate_paths(
        target_certificate=target_certificate,
        site_id=site_id,
        omd_root=omd_root,
    )

    return any(certificate_path.is_file() for certificate_path in target_certificate_paths)


def _run_cmkcert(
    omd_root: Path,
    site_id: SiteId,
    target_certificate: CertificateType,
    expiry: int,
    replace: bool,
) -> None:
    if (
        _cert_files_exist(
            target_certificate=target_certificate,
            site_id=site_id,
            omd_root=omd_root,
        )
        and not replace
    ):
        raise ValueError(
            f"{target_certificate} certificate already exists but '--replace' not given"
        )

    match target_certificate:
        case "site-ca":
            replace_site_ca(
                site_id=site_id,
                certificate_directory=cert_dir(omd_root),
                expiry=relativedelta(days=expiry),
            )

        case "agent-ca":
            replace_agent_ca(
                site_id=site_id,
                omd_root=omd_root,
                expiry=relativedelta(days=expiry),
            )

        case "site":
            replace_site_certificate(
                site_id=site_id,
                certificate_directory=cert_dir(omd_root),
                expiry=relativedelta(days=expiry),
            )

        case "broker-ca":
            replace_broker_ca(site_id=site_id, omd_root=omd_root, expiry=relativedelta(days=expiry))

        case "broker":
            replace_broker_certificate(
                site_id=site_id, omd_root=omd_root, expiry=relativedelta(days=expiry)
            )

        case _:
            raise ValueError(f"Unknown certificate type: {target_certificate}")


def main(args: Sequence[str]) -> int:
    parsed_args = _parse_args(args)

    site_id = os.environ.get("OMD_SITE")
    if not site_id:
        sys.stderr.write("cmk-cert: Checkmk can be used only as site user.\n")
        return -1

    try:
        _run_cmkcert(
            omd_root=cmk.utils.paths.omd_root,
            site_id=SiteId(site_id),
            target_certificate=parsed_args.target_certificate,
            expiry=parsed_args.expiry,
            replace=parsed_args.replace,
        )
    except (OSError, ValueError) as e:
        sys.stderr.write(f"cmk-cert: {e}\n")
        return -1

    sys.stdout.write(
        f"cmk-cert: {parsed_args.target_certificate} certificate rotated successfully.\n"
    )
    return 0

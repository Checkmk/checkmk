#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module contains the entry point for the cmk-cert utility.

Certificate initialization functionality is used by omd during site creation and must be quick.
If cmk-cert is run interactively in 'rotate' mode, the GUI functionality is imported on demand.
"""

import argparse
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import cmk.utils.paths
from cmk import messaging
from cmk.ccc.site import omd_site, SiteId
from cmk.crypto.certificate import serial_number_string
from cmk.crypto.issued_certificates import IssuedCertificatesComponent
from cmk.utils.certs import (
    agent_root_ca_path,
    cert_dir,
    crl_path,
    initialize_agent_ca,
    initialize_site_ca,
    initialize_site_certificate,
    issued_certificates_path,
    RelaysCA,
    revoke_certificate,
    SiteCA,
)

from .cmkcert_rotate import (
    finalize_rotate_site_ca_certificate,
    rotate_agent_ca_certificate,
    rotate_site_certificate,
    start_rotate_site_ca_certificate,
)

CertificateType = Literal["site", "site-ca", "agent-ca"]
IssuingCA = Literal["site-ca", "agent-ca", "relay-ca", "broker-ca", "customer-broker-ca"]


def _parse_serial_number(value: str) -> int:
    if not re.fullmatch("[0-9a-fA-F]+", digits := value.replace(":", "")):
        raise argparse.ArgumentTypeError(f"'{value}' is not a hexadecimal serial number.")
    return int(digits, 16)


def _parse_args(args: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""
Utility to initialize, rotate and revoke Checkmk certificates.

The utility supports three modes of operation: 'init', 'rotate' and 'revoke'.
See '%(prog)s <mode> --help' for more information about each mode.
"""
    )

    modes = parser.add_subparsers(dest="mode", required=True, description="Operation mode")
    mode_init = modes.add_parser(
        "init",
        help="Create a certificate that does not yet exist.",
        description="""
The 'init' mode creates a new certificate that does not yet exist with the default parameters.
It is intended for internal use during site creation.
""",
    )
    mode_init.add_argument(
        "target_certificate",
        choices=["site", "site-ca", "agent-ca"],
        help="Specify which certificate to create.",
    )

    mode_rotate = modes.add_parser(
        "rotate",
        help="Replace an existing certificate with a new one.",
        description="""\
The 'rotate' mode can be used to replace an existing certificate with a new one. \
Be sure to consult the notes below on the specific steps required for each certificate type.
""",
        epilog="""
Notes on rotating the available certificate types:

'site' certificate: The site certificate can be rotated directly. The new certificate \
will be signed by the existing Site CA certificate and take settings configured in WATO \
into account. After rotation, you need to reload the affected services to make use of the new \
certificate.

'site-ca' certificate: Rotating the Site CA certificate is a two-step process. \
First, a new Site CA certificate is generated and added to the trusted certificate store \
alongside the existing one. After reviewing and activating the pending changes in the GUI, \
the rotation can be finalized using '%(prog)s site-ca --finalize', which replaces the old \
Site CA certificate with the new one and generates a new site certificate signed by the new Site \
CA. After the finalization step, changes need to be activated in the GUI again to make use of the new \
Site CA and site certificates.
In a distributed monitoring setup, the rotation should be run from the central site to ensure \
that remote sites' trust stores are updated automatically.
Warning: following the Site CA certificate rotation, all agents will need to be manually \
re-registered to trust the updated certificate.

'agent-ca' certificate: The agent signing CA certificate can be rotated directly. The current CA \
is kept alongside the new one, so that already registered agents stay trusted and can renew their \
certificate with the new CA. Use '--ca-pem' to install your own CA instead of a generated one. \
Since the agent receiver authorizes registered agents by the common name of their certificate's \
issuer, the provided CA has to have the same common name as the current one. Use '--force' to \
install a CA with a different common name anyway, which requires registering all agents again. \
The provided CA also has to be a currently valid CA certificate that carries subject and \
authority key identifiers and a key of at least RSA 2048 bits or an equivalent elliptic curve \
key.
Once no agent uses a certificate issued by the previous CA anymore, delete it from \
'etc/ssl/agents' and reload the agent receiver to drop it from the trusted certificate store.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode_rotate.add_argument(
        "target_certificate",
        choices=["site", "site-ca", "agent-ca"],
        help="Specify which certificate to rotate.",
    )

    mode_rotate.add_argument(
        "--expiry",
        type=int,
        default=None,
        help=(
            "Specify the expiry time in days. "
            "The default expiry time is 10 years for all certificate types."
        ),
    )

    mode_rotate.add_argument(
        "--remote-site",
        dest="remote_site",
        type=str,
        help=("Specify the remote site id for which you want to rotate the certificate."),
    )
    mode_rotate.add_argument(
        "--ca-pem",
        dest="ca_pem",
        type=Path,
        default=None,
        help=(
            "'agent-ca' certificate only -- "
            "Install the CA from the given PEM file instead of generating a new CA. The file has "
            "to contain both the CA certificate and its unencrypted private key."
        ),
    )
    mode_rotate.add_argument(
        "--force",
        action="store_true",
        default=False,
        help=(
            "'agent-ca' certificate only -- "
            "Install the CA given by '--ca-pem' even if its common name differs from the current "
            "CA's. The agent receiver will then reject all registered agents until they are "
            "registered again."
        ),
    )
    mode_rotate.add_argument(
        "--finalize",
        action="store_true",
        default=False,
        help=(
            "'site-ca' certificate only -- "
            "Finalize the Site CA certificate rotation by replacing the old certificate with the new one and generating a new site certificate."
        ),
    )

    mode_revoke = modes.add_parser(
        "revoke",
        help="Revoke a certificate issued by one of the site's CAs.",
        description="""
The 'revoke' mode adds the serial number of a certificate to the certificate revocation list \
(CRL) of the CA that issued it. Each CA has its own CRL, stored next to its certificate, which is \
created if it does not exist yet. Only certificates that are recorded as issued in the certificate \
log of the CA in 'var/log' can be revoked, and the revocation is recorded there as well.
""",
    )
    mode_revoke.add_argument(
        "issuing_ca",
        choices=["site-ca", "agent-ca", "relay-ca", "broker-ca", "customer-broker-ca"],
        help="Specify the CA that issued the certificate to revoke.",
    )
    mode_revoke.add_argument(
        "serial_number",
        type=_parse_serial_number,
        help=(
            "Serial number of the certificate to revoke, in hexadecimal notation, with or "
            "without colons (e.g. '65:2e:18:0f' or '652e180f')."
        ),
    )
    mode_revoke.add_argument(
        "--customer",
        type=str,
        default=None,
        help=(
            "'customer-broker-ca' only -- "
            "Specify the customer whose message broker CA issued the certificate."
        ),
    )

    return parser.parse_args(args)


def _certificate_path(
    omd_root: Path,
    site_id: SiteId,
    target_certificate: CertificateType,
) -> Path:
    match target_certificate:
        case "site":
            return SiteCA.site_certificate_path(cert_dir=cert_dir(omd_root), site_id=site_id)
        case "site-ca":
            return SiteCA.root_ca_path(cert_dir=cert_dir(omd_root))
        case "agent-ca":
            return agent_root_ca_path(site_root_dir=omd_root)


def _run_init(
    omd_root: Path,
    site_id: SiteId,
    target_certificate: CertificateType,
    key_size: int | None = None,
) -> None:
    if _certificate_path(omd_root, site_id, target_certificate).exists():
        raise ValueError(f"Certificate '{target_certificate}' for site '{site_id}' already exists.")

    match target_certificate:
        case "site-ca":
            initialize_site_ca(site_id=site_id, omd_root=omd_root, key_size=key_size)
        case "agent-ca":
            initialize_agent_ca(site_id=site_id, omd_root=omd_root, key_size=key_size)
        case "site":
            initialize_site_certificate(site_id=site_id, omd_root=omd_root, key_size=key_size)


def _run_rotate(
    omd_root: Path,
    site_id: SiteId,
    target_certificate: CertificateType,
    expiry: int | None,
    finalize: bool,
    ca_pem: Path | None = None,
    force: bool = False,
) -> None:

    if (
        site_id == omd_site()
        and not (old_cert := _certificate_path(omd_root, site_id, target_certificate)).exists()
    ):
        raise ValueError(f"Certificate '{target_certificate}' not found at '{old_cert}'.")

    match target_certificate:
        case "site-ca":
            if finalize:
                finalize_rotate_site_ca_certificate(
                    omd_root=omd_root,
                    site_id=site_id,
                    expiry=expiry,
                    key_size=4096,
                )
            else:
                start_rotate_site_ca_certificate(
                    omd_root=omd_root,
                    site_id=site_id,
                    expiry=expiry,
                    key_size=4096,
                )
        case "site":
            rotate_site_certificate(
                omd_root=omd_root,
                site_id=site_id,
                expiry=expiry,
                key_size=4096,
            )
        case "agent-ca":
            rotate_agent_ca_certificate(
                omd_root=omd_root,
                site_id=site_id,
                expiry=expiry,
                key_size=4096,
                ca_pem=ca_pem,
                force=force,
            )


def _issuing_ca_files(
    omd_root: Path,
    site_id: SiteId,
    issuing_ca: IssuingCA,
    customer: str | None,
) -> tuple[Path, Path]:
    """Return the certificate and key file of the given CA, which are one combined file for some."""
    match issuing_ca:
        case "site-ca" | "agent-ca":
            combined = _certificate_path(omd_root, site_id, issuing_ca)
            return combined, combined
        case "relay-ca":
            combined = RelaysCA.root_ca_path(cert_dir=cert_dir(omd_root))
            return combined, combined
        case "broker-ca":
            return messaging.cacert_file(omd_root), messaging.ca_key_file(omd_root)
        case "customer-broker-ca":
            if customer is None:
                raise ValueError(
                    "Revoking a certificate of the 'customer-broker-ca' needs --customer."
                )
            return (
                messaging.multisite_cacert_file(omd_root, customer),
                messaging.multisite_ca_key_file(omd_root, customer),
            )


def _issued_certificates_component(issuing_ca: IssuingCA) -> IssuedCertificatesComponent:
    match issuing_ca:
        case "site-ca":
            return "sites"
        case "agent-ca":
            return "agents"
        case "relay-ca":
            return "relays"
        case "broker-ca" | "customer-broker-ca":
            return "messaging"


def _run_revoke(
    omd_root: Path,
    site_id: SiteId,
    issuing_ca: IssuingCA,
    serial_number: int,
    customer: str | None = None,
) -> None:
    cert_path, key_path = _issuing_ca_files(omd_root, site_id, issuing_ca, customer)
    for path in (cert_path, key_path):
        if not path.exists():
            raise ValueError(f"The '{issuing_ca}' CA is not available at '{path}'.")

    revoke_certificate(
        cert_path,
        key_path,
        serial_number,
        issued_certificates_path(omd_root, _issued_certificates_component(issuing_ca)),
    )
    sys.stdout.write(
        f"The certificate with serial number {serial_number_string(serial_number)} is revoked "
        f"in '{crl_path(cert_path)}'.\n"
    )


def main(args: Sequence[str] | None = None) -> int:
    if args is None:
        args = sys.argv[1:]
    parsed_args = _parse_args(args)

    site_id = os.environ.get("OMD_SITE")
    if not site_id:
        sys.stderr.write("cmk-cert: OMD_SITE not set.\n")
        return -1

    try:
        if parsed_args.mode == "init":
            _run_init(
                cmk.utils.paths.omd_root,
                SiteId(site_id),
                parsed_args.target_certificate,
            )

        elif parsed_args.mode == "rotate":
            if parsed_args.target_certificate == "site-ca":
                if parsed_args.finalize and parsed_args.expiry is not None:
                    sys.stderr.write(
                        "cmk-cert: --expiry may only be used in the first step of rotating the 'site-ca' certificate, not when finalizing.\n"
                    )
                    return -1
            elif parsed_args.finalize:
                sys.stderr.write(
                    "cmk-cert: --finalize can only be used when rotating the 'site-ca' certificate.\n"
                )
                return -1

            if parsed_args.target_certificate == "agent-ca":
                if parsed_args.remote_site:
                    sys.stderr.write(
                        "cmk-cert: --remote-site cannot be used when rotating the 'agent-ca' certificate.\n"
                    )
                    return -1
            elif parsed_args.ca_pem is not None:
                sys.stderr.write(
                    "cmk-cert: --ca-pem can only be used when rotating the 'agent-ca' certificate.\n"
                )
                return -1
            elif parsed_args.force:
                sys.stderr.write(
                    "cmk-cert: --force can only be used when rotating the 'agent-ca' certificate.\n"
                )
                return -1

            target_site = SiteId(parsed_args.remote_site or site_id)
            _run_rotate(
                cmk.utils.paths.omd_root,
                target_site,
                parsed_args.target_certificate,
                parsed_args.expiry,
                parsed_args.finalize,
                parsed_args.ca_pem,
                parsed_args.force,
            )

        elif parsed_args.mode == "revoke":
            if parsed_args.issuing_ca != "customer-broker-ca" and parsed_args.customer is not None:
                sys.stderr.write(
                    "cmk-cert: --customer can only be used when revoking a certificate issued by "
                    "the 'customer-broker-ca'.\n"
                )
                return -1

            _run_revoke(
                cmk.utils.paths.omd_root,
                SiteId(site_id),
                parsed_args.issuing_ca,
                parsed_args.serial_number,
                parsed_args.customer,
            )

        else:
            sys.stderr.write(f"cmk-cert: Unknown mode '{parsed_args.mode}'.\n")
            return -1

    except (OSError, ValueError, RuntimeError) as e:
        sys.stderr.write(f"cmk-cert: {e}\n")
        return -1

    return 0

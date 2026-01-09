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
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.utils.certs import (
    agent_root_ca_path,
    cert_dir,
    initialize_agent_ca,
    initialize_site_ca,
    initialize_site_certificate,
    SiteCA,
)

CertificateType = Literal["site", "site-ca", "agent-ca"]


def _parse_args(args: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""
Utility to initialize and rotate Checkmk certificates.

The utility supports two modes of operation: 'init' and 'rotate'.
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

'agent-ca' certificate: Rotating the Agent CA certificate is an experimental feature \
and requires manual re-registration of all agents to trust the new certificate. Use with caution.
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
            "The default expiry time depends on the target certificate: 10 years for 'site-ca' "
            "and 'agent-ca', 2 years for 'site' certificates."
        ),
    )

    mode_rotate.add_argument(
        "--remote-site",
        dest="remote_site",
        type=str,
        help=(
            "'site-ca' certificate only -- "
            "Specify the remote site id for which you want to rotate the certificate."
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
) -> None:
    # we import the expensive GUI module only if we really need it
    import cmk.gui.cmkcert_rotate as rotate

    if not (old_cert := _certificate_path(omd_root, site_id, target_certificate)).exists():
        raise ValueError(f"Certificate '{target_certificate}' not found at '{old_cert}'.")

    match target_certificate:
        case "site-ca":
            if finalize:
                rotate.finalize_rotate_site_ca_certificate(
                    omd_root=omd_root,
                    site_id=site_id,
                    expiry=expiry,
                    key_size=4096,
                )
            else:
                rotate.start_rotate_site_ca_certificate(
                    omd_root=omd_root,
                    site_id=site_id,
                    expiry=expiry,
                    key_size=4096,
                )

        case "agent-ca":
            rotate.rotate_agent_ca_certificate(
                omd_root=omd_root,
                site_id=site_id,
                expiry=expiry,
                key_size=4096,
            )

        case "site":
            rotate.rotate_site_certificate(
                omd_root=omd_root,
                site_id=site_id,
                expiry=expiry,
                key_size=4096,
            )


def main(args: Sequence[str]) -> int:
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
            elif parsed_args.remote_site or parsed_args.finalize:
                sys.stderr.write(
                    "cmk-cert: --remote-site and --finalize can only be used when rotating the 'site-ca' certificate.\n"
                )
                return -1

            target_site = SiteId(parsed_args.remote_site or site_id)
            _run_rotate(
                cmk.utils.paths.omd_root,
                target_site,
                parsed_args.target_certificate,
                parsed_args.expiry,
                parsed_args.finalize,
            )

        else:
            sys.stderr.write(f"cmk-cert: Unknown mode '{parsed_args.mode}'.\n")
            return -1

    except (OSError, ValueError, RuntimeError) as e:
        sys.stderr.write(f"cmk-cert: {e}\n")
        return -1

    return 0

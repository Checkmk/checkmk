#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import argparse
import json
import os
import shutil
import sys
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dateutil.relativedelta import relativedelta

import cmk.gui.watolib.changes as _changes
import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.gui import main_modules
from cmk.gui.config import load_config
from cmk.gui.site_config import site_is_local
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.activate_changes import (
    ActivateChanges,
)
from cmk.gui.watolib.automations import (
    do_remote_automation,
    make_automation_config,
)
from cmk.gui.watolib.config_domain_name import (
    config_variable_registry,
)
from cmk.gui.watolib.config_domains import (
    ConfigDomainCACertificates,
    ConfigDomainSiteCertificate,
)
from cmk.gui.watolib.global_settings import (
    load_configuration_settings,
    save_global_settings,
)
from cmk.utils.automation_config import RemoteAutomationConfig
from cmk.utils.certs import (
    agent_root_ca_path,
    cert_dir,
    CertManagementEvent,
    RootCA,
    SiteCA,
)
from cmk.utils.log.security_event import log_security_event

CertificateType = Literal["site", "site-ca", "agent-ca"]

CERTIFICATE_DIRECTORY = cert_dir(cmk.utils.paths.omd_root)
CERTIFICATE_TMP_PATH = CERTIFICATE_DIRECTORY / "temp_certificate"
TEMPORARY_CA_FILE_PATH = Path(CERTIFICATE_TMP_PATH / "ca.pem")
TEMPORARY_TARGET_SITE_FILE_PATH = Path(CERTIFICATE_TMP_PATH / "target_site.json")


@dataclass
class Args:
    target_certificate: CertificateType
    expiry: int
    remote_site: str
    finalize: bool


def _parse_args(args: Sequence[str]) -> Args:
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "target_certificate",
        choices=["site", "site-ca", "agent-ca"],
        help="specify which certificate to create",
    )
    parser.add_argument(
        "--expiry",
        type=int,
        default=90,
        help="specify the expiry time in days",
    )
    parser.add_argument(
        "--remote-site",
        dest="remote_site",
        type=str,
        help="specify the remote site id for which you want to rotate the certificate",
    )
    parser.add_argument(
        "--finalize",
        action="store_true",
        default=False,
        help=(
            "finalize the certificate rotation by replacing overwriting the old site-ca with "
            "the new one that was previously generate, then a new site certificate is created"
        ),
    )

    parsed_args = parser.parse_args(args)

    return Args(
        target_certificate=parsed_args.target_certificate,
        expiry=parsed_args.expiry,
        remote_site=parsed_args.remote_site,
        finalize=parsed_args.finalize,
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

        case _:
            raise ValueError(f"Unknown certificate type: {target_certificate}")


def replace_site_certificate(
    site_id: SiteId,
    certificate_directory: Path,
    expiry: relativedelta,
    key_size: int = 4096,
) -> None:
    site_ca = SiteCA.load(certificate_directory=certificate_directory)

    sans = (
        ConfigDomainSiteCertificate().load_full_config().get("site_subject_alternative_names", [])
    )
    site_ca.create_site_certificate(
        site_id=site_id,
        additional_sans=sans,
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


def stage_replace_site_ca(
    site_id: SiteId,
    expiry: relativedelta,
    key_size: int = 4096,
) -> None:
    """
    Stage site-CA certificate rotation.

    It initiates the rotation process by:
    1. Generating a new site-CA certificate.
    2. Storing this new certificate in a temporary folder.
    3. Adding the new certificate to the trusted certificate store alongside the
    existing one, ensuring continuity.
    """
    site_ca: SiteCA | None = None

    if TEMPORARY_TARGET_SITE_FILE_PATH.exists():
        sys.stderr.write(
            f"cmk-cert: aborting, rotation target found in {TEMPORARY_TARGET_SITE_FILE_PATH}, "
            "please ensure the current rotation is finalized by using the --finalize argument "
            "before initiating a new rotation.\n"
        )
        return

    sys.stdout.write(
        "cmk-cert: Rotating the Site CA certificate now. Note that, if you are "
        "running this command from a remote site you have to add the new Site CA "
        "certificate to the central site's global trust store manually.\n"
        "Run this command with the --remote argument from the central site instead to avoid this.\n"
    )

    # Handle the site-ca certificate rotation
    if errors := main_modules.get_failed_plugins():
        sys.stderr.write(f"The following errors occurred during plug-in loading: {errors!r}\n")
        return
    with gui_context():
        varname = "trusted_certificate_authorities"
        current_settings = load_configuration_settings()
        new_settings = dict(deepcopy(current_settings))
        config = load_config()

        # Check if there are any pending changes to ensure that the site is in a stable state
        if ActivateChanges.get_number_of_pending_changes(
            sites=list(config.sites),
            count_limit=1,
        ):
            sys.stderr.write("cmk-cert: aborting, there are still pending changes to review\n")
            return

        if (site_config := config.sites.get(site_id)) is None:
            sys.stderr.write(f"cmk-cert: aborting, site {site_id} does not exist\n")
            return

        CERTIFICATE_TMP_PATH.mkdir(parents=True, exist_ok=True)

        with open(TEMPORARY_TARGET_SITE_FILE_PATH, "w") as outfile:
            json.dump({"target_site": str(site_id)}, outfile)

        # Stage local site certificate rotation
        if site_is_local(site_config):
            site_ca = SiteCA.create(
                cert_dir=Path(CERTIFICATE_TMP_PATH),
                site_id=SiteId(site_id),
                expiry=expiry,
                key_size=key_size,
            )
            site_ca_certificate = site_ca.root_ca.certificate.dump_pem().bytes.decode("utf-8")
            new_settings[varname]["trusted_cas"].append(site_ca_certificate)

        # Stage remote site certificate rotation
        else:
            automation_config = make_automation_config(site_config=site_config)
            assert isinstance(automation_config, RemoteAutomationConfig)

            automation_response = do_remote_automation(
                automation_config,
                "stage-certificate-rotation",
                vars_=[
                    ("site_id", site_id),
                    ("expiry", str(expiry.days)),
                    ("key_size", str(key_size)),
                ],
                timeout=120,
                debug=True,
            )
            assert isinstance(automation_response, str)
            Certificate.load_pem(CertificatePEM(automation_response))
            new_settings[varname]["trusted_cas"].append(automation_response)

        # Add site-ca certificate to the trusted store
        save_global_settings(new_settings)
        ConfigDomainCACertificates.log_changes(current_settings.get(varname), new_settings[varname])
        config_variable = config_variable_registry[varname]

        _changes.add_change(
            action_name="edit-configvar",
            text=f"Added new Site CA certificate for site {site_id} to trusted CAs store",
            user_id=None,
            sites=list(config.sites.keys()),
            domains=list(config_variable.all_domains()),
            need_sync=True,
            need_restart=True,
            need_apache_reload=True,
            domain_settings={
                domain.ident(): {"need_apache_reload": config_variable.need_apache_reload()}
                for domain in config_variable.all_domains()
            },
            use_git=config.wato_use_git,
        )

        sys.stdout.write(
            "cmk-cert: site-ca certificate rotation successfully initialized, "
            "please review the pending changes before finalizing the rotation.\n"
        )


def finalize_replace_site_ca(
    site_id: SiteId,
    certificate_directory: Path,
    expiry: relativedelta,
    key_size: int = 4096,
) -> None:
    """
    Finalizes the rotation of the site-CA certificate by promoting the staged certificate.

    This function assumes a new site-CA certificate has been previously generated and
    stored in the temporary staging folder by the stagin function.
    It performs the final step of rotation by replacing the current site-CA certificate
    with the new certificate from the temporary folder.
    """
    rotating_site_id = ""

    if not TEMPORARY_TARGET_SITE_FILE_PATH.exists():
        sys.stderr.write("cmk-cert: aborting, no certificate rotation to finalize.\n")
        return

    with open(TEMPORARY_TARGET_SITE_FILE_PATH) as infile:
        rotating_site_id = json.load(infile)["target_site"]

    if not rotating_site_id:
        sys.stderr.write(
            "cmk-cert: aborting, no certificate rotation to finalize: failed to read "
            f"state file ({TEMPORARY_TARGET_SITE_FILE_PATH}).\n"
        )
        return

    if rotating_site_id and str(site_id) != rotating_site_id:
        sys.stderr.write(
            f"cmk-cert: aborting, can not finalize the rotation of site {site_id} "
            f"while another rotation for site {rotating_site_id} is currently in "
            "progress.\n"
        )
        return

    if errors := main_modules.get_failed_plugins():
        sys.stderr.write(f"The following errors occurred during plug-in loading: {errors!r}\n")
        return
    with gui_context():
        config = load_config()

        # Check if the pending changes for the staging phase have been successfully activated
        if ActivateChanges.get_number_of_pending_changes(
            sites=list(config.sites),
            count_limit=1,
        ):
            sys.stderr.write("cmk-cert: aborting, there are still pending changes to review\n")
            return

        if (site_config := config.sites.get(site_id)) is None:
            sys.stderr.write(f"cmk-cert: aborting, site {site_id} does not exist\n")
            return

        # Finalize local site certificate rotation
        if site_is_local(site_config):
            if not TEMPORARY_CA_FILE_PATH.exists():
                sys.stderr.write(
                    f"cmk-cert: aborting, temporary certificate not found in {TEMPORARY_CA_FILE_PATH}, "
                    "please run the script initially without the --finalize option.\n"
                )
                return

            site_ca = SiteCA.load(certificate_directory=CERTIFICATE_TMP_PATH)
            shutil.move(TEMPORARY_CA_FILE_PATH, Path(certificate_directory / "ca.pem"))

            replace_site_certificate(
                site_id=SiteId(site_id),
                certificate_directory=certificate_directory,
                expiry=expiry,
                key_size=key_size,
            )

            site_cert = SiteCA.load_site_certificate(
                cert_dir=certificate_directory, site_id=SiteId(site_id)
            )

            log_security_event(
                CertManagementEvent(
                    event="certificate rotated",
                    component="site certificate",
                    actor="cmk-cert",
                    cert=site_cert.certificate if site_cert else None,
                )
            )

            log_security_event(
                CertManagementEvent(
                    event="certificate rotated",
                    component="site certificate authority",
                    actor="cmk-cert",
                    cert=site_ca.root_ca.certificate,
                )
            )

        # Finalize remote site certificate rotation
        else:
            automation_config = make_automation_config(site_config=site_config)
            assert isinstance(automation_config, RemoteAutomationConfig)

            automation_response = do_remote_automation(
                automation_config,
                "finalize-certificate-rotation",
                vars_=[
                    ("site_id", site_id),
                    ("expiry", str(expiry.days)),
                    ("key_size", str(key_size)),
                ],
                timeout=120,
                debug=True,
            )
            assert isinstance(automation_response, str)
            if automation_response != "success":
                raise ValueError(
                    f"automation response for {site_id} was not 'success', instead "
                    f"it was received: {automation_response}"
                )

        shutil.rmtree(CERTIFICATE_TMP_PATH, ignore_errors=True)

        sys.stdout.write(
            "cmk-cert: site-ca certificate rotation successfully finalized, please "
            "manually remove the old certificate from the trusted store and "
            "restart the sites.\n"
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


def _run_cmkcert(
    omd_root: Path,
    site_id: SiteId,
    target_certificate: CertificateType,
    expiry: int,
    finalize: bool,
) -> None:
    match target_certificate:
        case "site-ca":
            if not finalize:
                stage_replace_site_ca(
                    site_id=site_id,
                    expiry=relativedelta(days=expiry),
                )
            else:
                finalize_replace_site_ca(
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
            site_id=(
                SiteId(site_id) if not parsed_args.remote_site else SiteId(parsed_args.remote_site)
            ),
            target_certificate=parsed_args.target_certificate,
            expiry=parsed_args.expiry,
            finalize=parsed_args.finalize,
        )
    except (OSError, ValueError) as e:
        sys.stderr.write(f"cmk-cert: {e}\n")
        return -1

    if parsed_args.target_certificate != "site-ca":
        sys.stdout.write(
            f"cmk-cert: {parsed_args.target_certificate} certificate rotated successfully.\n"
        )
    return 0

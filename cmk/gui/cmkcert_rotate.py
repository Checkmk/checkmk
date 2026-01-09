#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module implements certificate rotation and is used by the cmk-cert utility.

Rotating certificates can require multiple steps, automatically create changes, run automations.
The help text of cmk-cert provides an overview to these procedures.

This module is separated from cmk.gui.cmkcert to allow conditional imports of GUI modules.
"""

import json
import os
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from dateutil.relativedelta import relativedelta

from livestatus import SiteConfiguration

import cmk.gui.site_config
import cmk.gui.watolib.changes
import cmk.gui.watolib.global_settings
from cmk.ccc.site import SiteId
from cmk.crypto.certificate import Certificate, CertificatePEM, CertificateWithPrivateKey
from cmk.gui import main_modules
from cmk.gui.config import Config, load_config
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.activate_changes import ActivateChanges
from cmk.gui.watolib.automations import (
    do_remote_automation,
    ENV_VARIABLE_FORCE_CLI_INTERFACE,
    make_automation_config,
)
from cmk.gui.watolib.config_domain_name import config_variable_registry
from cmk.gui.watolib.config_domains import ConfigDomainCACertificates, ConfigDomainSiteCertificate
from cmk.utils.automation_config import RemoteAutomationConfig
from cmk.utils.certs import (
    agent_root_ca_path,
    cert_dir,
    CertManagementEvent,
    RootCA,
    SiteCA,
)
from cmk.utils.log.security_event import log_security_event


@contextmanager
def _force_automations_cli_interface() -> Iterator[None]:
    try:
        os.environ[ENV_VARIABLE_FORCE_CLI_INTERFACE] = "True"
        yield
    finally:
        os.environ.pop(ENV_VARIABLE_FORCE_CLI_INTERFACE, None)


@contextmanager
def _site_gui_context(site_id: SiteId) -> Iterator[tuple[SiteConfiguration, Config]]:
    if errors := main_modules.get_failed_plugins():
        raise RuntimeError(f"The following errors occurred during plug-in loading: {errors!r}")

    with gui_context(), _force_automations_cli_interface():
        config = load_config()
        if (site_config := config.sites.get(site_id)) is None:
            raise ValueError(f"Aborting, site {site_id} does not exist")

        if ActivateChanges.get_number_of_pending_changes(sites=list(config.sites), count_limit=1):
            raise ValueError("Aborting, there are still pending changes to review")

        yield site_config, config


def _scratch_dir(omd_root: Path) -> Path:
    scratch_dir = cert_dir(omd_root) / "pending_certificate_rotation"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return scratch_dir


def _ca_rotation_state_file_path(omd_root: Path) -> Path:
    return _scratch_dir(omd_root) / "state.json"


def start_rotate_site_ca_certificate(
    omd_root: Path,
    site_id: SiteId,
    expiry: int | None = None,
    key_size: int = 4096,
) -> None:
    """
    Stage Site CA certificate rotation.

    It initiates the rotation process by:
    1. Generating a new Site CA certificate.
    2. Storing this new certificate in a temporary folder.
    3. Adding the new certificate to the trusted certificate store alongside the existing one.
    """
    expiry_ = relativedelta(days=expiry) if expiry is not None else relativedelta(years=10)

    state_file = _ca_rotation_state_file_path(omd_root)
    if state_file.exists():
        raise ValueError(
            f"Aborting, rotation target found in {state_file}, "
            "please ensure the current rotation is finalized by using the --finalize argument "
            "before initiating a new rotation."
        )

    # TODO detect if this is a local rotation on a remote site and warn about it

    with _site_gui_context(site_id) as (site, config):
        current_settings = cmk.gui.watolib.global_settings.load_configuration_settings()
        new_settings = dict(current_settings)

        # Record the target site for which the rotation is initiated
        state_file.write_text(json.dumps({"target_site": str(site_id)}))

        # Stage local site certificate rotation
        if cmk.gui.site_config.site_is_local(site):
            site_ca = SiteCA.create(
                cert_dir=_scratch_dir(omd_root),
                site_id=SiteId(site_id),
                expiry=expiry_,
                key_size=key_size,
            )
            new_ca_certificate = site_ca.root_ca.certificate.dump_pem().bytes.decode("utf-8")

        # Stage remote site certificate rotation
        else:
            automation_config = make_automation_config(site)
            assert isinstance(automation_config, RemoteAutomationConfig)

            automation_response = do_remote_automation(
                automation_config,
                "stage-certificate-rotation",
                vars_=[
                    ("site_id", site_id),
                    ("expiry", str(expiry_.days)),
                    ("key_size", str(key_size)),
                ],
                timeout=120,
                debug=True,
            )
            assert isinstance(automation_response, str)
            # Verify that the received certificate is valid
            Certificate.load_pem(CertificatePEM(automation_response))
            new_ca_certificate = automation_response

        # Add site-ca certificate to the trusted store
        new_settings["trusted_certificate_authorities"]["trusted_cas"].append(new_ca_certificate)
        cmk.gui.watolib.global_settings.save_global_settings(new_settings)
        ConfigDomainCACertificates.log_changes(
            current_settings.get("trusted_certificate_authorities"),
            new_settings["trusted_certificate_authorities"],
        )
        config_variable = config_variable_registry["trusted_certificate_authorities"]

        cmk.gui.watolib.changes.add_change(
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
            "cmk-cert: Site CA certificate rotation successfully initialized, please review and "
            "activate the pending changes in WATO before finalizing the rotation.\n"
        )


def finalize_rotate_site_ca_certificate(
    omd_root: Path,
    site_id: SiteId,
    expiry: int | None = None,
    key_size: int = 4096,
) -> None:
    """
    Finalizes the rotation of the Site CA certificate by promoting the staged certificate.

    This function assumes a new Site CA generated and
    stored in the temporary staging folder by the stagin function.
    It performs the final step of rotation by replacing the current Site CA certificate
    with the new certificate from the temporary folder.
    """
    expiry_ = relativedelta(days=expiry) if expiry is not None else relativedelta(years=10)

    state_file = _ca_rotation_state_file_path(omd_root)
    if not state_file.exists():
        raise ValueError("Aborting, no certificate rotation to finalize: state file not found")

    rotating_site_id = json.loads(state_file.read_text()).get("target_site", "")
    if not rotating_site_id:
        raise ValueError("Aborting, no certificate rotation to finalize: failed to read state file")
    if site_id != SiteId(rotating_site_id):
        raise ValueError("Aborting, site ID does not match the one in the state file")

    with _site_gui_context(site_id) as (site, _):
        # Finalize local site certificate rotation
        if cmk.gui.site_config.site_is_local(site):
            if not (staged_ca_path := SiteCA.root_ca_path(_scratch_dir(omd_root))).exists():
                raise ValueError("Aborting, temporary certificate not found")

            shutil.move(staged_ca_path, SiteCA.root_ca_path(cert_dir(omd_root)))
            log_security_event(
                CertManagementEvent(
                    event="certificate rotated",
                    component="site certificate authority",
                    actor="cmk-cert",
                    cert=SiteCA.load(cert_dir(omd_root)).root_ca.certificate,
                )
            )

            # Rotate site certificate as well to make use of the new CA
            # We'll use the default settings, if they want to change expiry they just have to
            # rotate the site certificate again.
            rotate_site_certificate(omd_root=omd_root, site_id=site_id)

        # Finalize remote site certificate rotation
        else:
            automation_config = make_automation_config(site)
            assert isinstance(automation_config, RemoteAutomationConfig)

            automation_response = do_remote_automation(
                automation_config,
                "finalize-certificate-rotation",
                vars_=[
                    ("site_id", site_id),
                    ("expiry", str(expiry_.days)),
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

        shutil.rmtree(_scratch_dir(omd_root), ignore_errors=True)

        sys.stdout.write(
            "cmk-cert: Site CA certificate rotation successfully finalized, please "
            "manually remove the old certificate from the trust store and "
            "restart the sites.\n"
        )


def rotate_agent_ca_certificate(
    omd_root: Path,
    site_id: SiteId,
    expiry: int | None = None,
    key_size: int = 4096,
) -> None:
    if sys.stdout.isatty():
        answer = input(
            "cmk-cert: Warning: rotating the agent CA certificate is experimental and requires manual "
            "re-registration of all agents.\nDo you want to continue? (y/N): "
        )
        if answer.strip().lower() not in ("y", "yes"):
            sys.stdout.write("Aborted.")
            sys.exit(1)

    new_ca = RootCA.create(
        path=agent_root_ca_path(site_root_dir=omd_root),
        name=f"Site '{site_id}' agent signing CA",
        validity=relativedelta(days=expiry) if expiry is not None else relativedelta(years=10),
        key_size=key_size or 4096,
    )

    log_security_event(
        CertManagementEvent(
            event="certificate rotated",
            component="agent certificate authority",
            actor="cmk-cert",
            cert=new_ca.certificate,
        )
    )


def rotate_site_certificate(
    omd_root: Path,
    site_id: SiteId,
    expiry: int | None = None,
    key_size: int = 4096,
) -> CertificateWithPrivateKey:
    sans = (
        ConfigDomainSiteCertificate().load_full_config().get("site_subject_alternative_names", [])
    )

    certificate_directory = cert_dir(omd_root)
    site_ca = SiteCA.load(certificate_directory)
    site_ca.create_site_certificate(
        site_id=site_id,
        additional_sans=sans,
        expiry=relativedelta(days=expiry) if expiry is not None else relativedelta(years=2),
        key_size=key_size or 4096,
    )

    site_cert = site_ca.load_site_certificate(certificate_directory, site_id)
    if not site_cert:
        raise RuntimeError(f"Failed to load newly created site certificate for site {site_id}")

    log_security_event(
        CertManagementEvent(
            event="certificate rotated",
            component="site certificate",
            actor="cmk-cert",
            cert=site_cert.certificate,
        )
    )

    return site_cert

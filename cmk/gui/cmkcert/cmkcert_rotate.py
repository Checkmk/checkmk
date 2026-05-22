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
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from dateutil.relativedelta import relativedelta

from livestatus import SiteConfiguration, SiteConfigurations

import cmk.gui.site_config
from cmk.ccc.site import omd_site, SiteId
from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.gui.config import load_config
from cmk.gui.user_sites import activation_sites
from cmk.gui.wato._check_mk_configuration import ConfigVariableTrustedCertificateAuthorities
from cmk.gui.watolib.activate_changes import ActivateChanges
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.automations import (
    do_remote_automation,
    ENV_VARIABLE_FORCE_CLI_INTERFACE,
    make_automation_config,
)
from cmk.gui.watolib.config_domains import ConfigDomainCACertificates, ConfigDomainSiteCertificate
from cmk.gui.watolib.pending_changes import (
    Change,
    ChangeScope,
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.utils.automation_config import RemoteAutomationConfig
from cmk.utils.certs import (
    cert_dir,
    CertManagementEvent,
    SiteCA,
)
from cmk.utils.security_event import log_security_event


@contextmanager
def _force_automations_cli_interface() -> Iterator[None]:
    try:
        os.environ[ENV_VARIABLE_FORCE_CLI_INTERFACE] = "True"
        yield
    finally:
        os.environ.pop(ENV_VARIABLE_FORCE_CLI_INTERFACE, None)


def _verify_site(site_id: SiteId, site_config: SiteConfigurations) -> SiteConfiguration:
    if (site := site_config.get(site_id)) is None:
        raise ValueError(f"Aborting, site {site_id} does not exist")

    if ActivateChanges.get_number_of_pending_changes(sites=list(site_config), count_limit=1):
        raise ValueError("Aborting, there are still pending changes to review")

    return site


def _days_until_10_years_from_today() -> int:
    """Calculate the number of days from today until 10 years later."""
    today = date.today()
    if today.month == 2 and today.day == 29:
        # We gift a free day on leap years
        today = date(today.year, 3, 1)

    ten_years_later = today.replace(year=today.year + 10)
    return (ten_years_later - today).days


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
    expiry_ = _days_until_10_years_from_today() if expiry is None else expiry

    state_file = _ca_rotation_state_file_path(omd_root)
    if state_file.exists():
        raise ValueError(
            f"Aborting, rotation target found in {state_file}, "
            "please ensure the current rotation is finalized by using the --finalize argument "
            "before initiating a new rotation."
        )

    config = load_config()
    site = _verify_site(site_id, config.sites)
    with _force_automations_cli_interface():
        ca_domain = ConfigDomainCACertificates()
        current_ca_settings = ca_domain.load_full_config()
        new_ca_settings = dict(current_ca_settings)
        new_ca_settings.setdefault(
            "trusted_certificate_authorities",
            ca_domain.default_globals()["trusted_certificate_authorities"],
        )

        is_local_rotation = cmk.gui.site_config.site_is_local(site)

        if sys.stdout.isatty():
            answer = input(
                "cmk-cert: Warning: rotating the site CA certificate requires manual re-registration "
                f"of all agents.\nYou are now rotating {'the local' if is_local_rotation else 'a remote'} "
                "site-ca certificate, do you want to continue? (y/N): "
            )
            if answer.strip().lower() not in ("y", "yes"):
                sys.stdout.write("Aborted.\n")
                sys.exit(1)

        # Record the target site for which the rotation is initiated
        state_file.write_text(json.dumps({"target_site": str(site_id)}))

        # Stage local site certificate rotation
        if is_local_rotation:
            site_ca = SiteCA.create(
                cert_dir=_scratch_dir(omd_root),
                site_id=SiteId(site_id),
                expiry=relativedelta(days=expiry_),
                key_size=key_size,
            )
            new_ca_certificate = site_ca.root_ca.certificate.dump_pem().bytes.decode("utf-8")

        # Stage remote site certificate rotation
        else:
            automation_config = make_automation_config(site)
            assert isinstance(automation_config, RemoteAutomationConfig)

            automation_response = do_remote_automation(
                automation_config,
                "stage-site-ca-certificate-rotation",
                vars_=[
                    ("site_id", site_id),
                    ("expiry", str(expiry_)),
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
        new_ca_settings["trusted_certificate_authorities"]["trusted_cas"].append(new_ca_certificate)
        ca_domain.save(new_ca_settings)
        ConfigDomainCACertificates.log_changes(
            current_ca_settings.get("trusted_certificate_authorities"),
            new_ca_settings["trusted_certificate_authorities"],
        )

        PendingChanges(
            activation_sites=activation_sites(config.sites),
            local_site=omd_site(),
            acting_user=None,
            store=PendingChangesStore(),
            hooks=(
                make_audit_log_change_hook(use_git=config.wato_use_git),
                index_update_change_hook,
            ),
        ).add(
            Change(
                action_name="edit-configvar",
                text=f"Added new Site CA certificate for site {site_id} to trusted CAs store",
                domains=[ca_domain.ident()],
                domain_settings={
                    ca_domain.ident(): {
                        "need_apache_reload": ConfigVariableTrustedCertificateAuthorities.need_apache_reload()
                    }
                },
                force_sync=True,
                force_restart=True,
                force_apache_reload=True,
            ),
            ChangeScope.sites(config.sites.keys()),
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
    expiry_ = _days_until_10_years_from_today() if expiry is None else expiry

    state_file = _ca_rotation_state_file_path(omd_root)
    if not state_file.exists():
        raise ValueError("Aborting, no certificate rotation to finalize: state file not found")

    rotating_site_id = json.loads(state_file.read_text()).get("target_site", "")
    if not rotating_site_id:
        raise ValueError("Aborting, no certificate rotation to finalize: failed to read state file")
    if site_id != SiteId(rotating_site_id):
        raise ValueError("Aborting, site ID does not match the one in the state file")

    site = _verify_site(site_id, load_config().sites)
    with _force_automations_cli_interface():
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
                "finalize-site-ca-certificate-rotation",
                vars_=[
                    ("site_id", site_id),
                    ("expiry", str(expiry_)),
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


def rotate_local_site_certificate(
    certificate_directory: Path,
    site_id: SiteId,
    additional_sans: Sequence[str],
    expiry: int,
    key_size: int = 4096,
) -> None:
    site_ca = SiteCA.load(certificate_directory)
    site_ca.create_site_certificate(
        site_id=site_id,
        additional_sans=additional_sans,
        expiry=relativedelta(days=expiry),
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


def rotate_site_certificate(
    omd_root: Path,
    site_id: SiteId,
    expiry: int | None = None,
    key_size: int = 4096,
) -> None:
    expiry_ = _days_until_10_years_from_today() if expiry is None else expiry

    site = _verify_site(site_id, load_config().sites)
    with _force_automations_cli_interface():
        if cmk.gui.site_config.site_is_local(site):
            sans = (
                ConfigDomainSiteCertificate()
                .load_full_config()
                .get("site_subject_alternative_names", [])
            )
            rotate_local_site_certificate(cert_dir(omd_root), site_id, sans, expiry_, key_size)

        else:
            automation_config = make_automation_config(site)
            assert isinstance(automation_config, RemoteAutomationConfig)

            automation_response = do_remote_automation(
                automation_config,
                "site-certificate-rotation",
                vars_=[
                    ("site_id", site_id),
                    ("expiry", str(expiry_)),
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

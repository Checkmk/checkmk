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
import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID
from dateutil.relativedelta import relativedelta

import cmk.gui.site_config
from cmk.ccc.site import omd_site, SiteId
from cmk.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateWithPrivateKey,
    InvalidExpiryError,
)
from cmk.crypto.keys import PublicKey
from cmk.crypto.pem import PEMDecodingError
from cmk.gui.config import load_config
from cmk.gui.log import logger
from cmk.gui.site_config import all_activation_sites
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
from cmk.livestatus_client import SiteConfiguration, SiteConfigurations
from cmk.utils.automation_config import RemoteAutomationConfig
from cmk.utils.certs import (
    agent_root_ca_path,
    cert_dir,
    CertManagementEvent,
    RootCA,
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

    changes = ActivateChanges()
    changes.load(sites=list(site_config), site_configs=site_config)
    if changes.has_pending_changes():
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
        log_security_event(
            CertManagementEvent(
                event="certificate added",
                component="trusted certificate authorities",
                actor="cmk-cert",
                cert=Certificate.load_pem(CertificatePEM(new_ca_certificate)),
            )
        )

        PendingChanges(
            activation_sites=all_activation_sites(config.sites),
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


# Minimum key sizes accepted by OpenSSL security level 2, which the distributions we support
# configure as their default.
_MINIMUM_RSA_KEY_SIZE = 2048
_MINIMUM_EC_KEY_SIZE = 256


def _key_is_strong_enough(public_key: PublicKey) -> bool:
    key = public_key.key
    if isinstance(key, rsa.RSAPublicKey):
        return key.key_size >= _MINIMUM_RSA_KEY_SIZE
    if isinstance(key, ec.EllipticCurvePublicKey):
        return key.curve.key_size >= _MINIMUM_EC_KEY_SIZE
    return True  # Ed25519 and Ed448 keys have a fixed and sufficient size


def _allows_agent_tls_connections(certificate: Certificate) -> bool:
    """Check that an extended key usage, if present, allows both agent certificate roles."""
    try:
        usages = set(certificate.get_extension_for_class(x509.ExtendedKeyUsage).value)
    except x509.ExtensionNotFound:
        return True

    # Note that OpenSSL does not accept 'anyExtendedKeyUsage' here, both usages have to be listed.
    return {ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH} <= usages


def _has_subject_key_identifier(certificate: Certificate) -> bool:
    try:
        certificate.get_extension_for_class(x509.SubjectKeyIdentifier)
    except x509.ExtensionNotFound:
        return False
    return True


def _agent_ca_requirement_violation(certificate: Certificate) -> str | None:
    """Describe why a certificate cannot serve as the agent signing CA, None if it can."""
    if not certificate.may_sign_certificates():
        return "it may not sign other certificates (CA flag or keyCertSign bit missing)"

    # The rotated CAs share their subject name, so their key identifiers are what tells the
    # certificates in the agents' trust store apart.
    if not _has_subject_key_identifier(certificate):
        return "it has no subject key identifier, which conforming CA certificates must have"

    if not certificate.has_authority_key_identifier():
        return "it has no authority key identifier, which conforming CA certificates must have"

    try:
        certificate.verify_expiry()
    except InvalidExpiryError as e:
        return f"it is not valid at the moment: {e}"

    if not _key_is_strong_enough(certificate.public_key):
        return (
            f"its {certificate.public_key.show_type()} key is too weak, at least "
            f"RSA {_MINIMUM_RSA_KEY_SIZE} bits or an equivalent elliptic curve key is required"
        )

    if not _allows_agent_tls_connections(certificate):
        return (
            "its extended key usage does not allow both TLS server and TLS client "
            "authentication, which the certificates it issues need"
        )

    return None


def _load_provided_agent_ca(ca_pem_file: Path) -> RootCA:
    """Load and validate a user provided CA from its PEM file."""
    try:
        ca = CertificateWithPrivateKey.load_combined_file_content(
            ca_pem_file.read_text(), passphrase=None
        )
    except (PEMDecodingError, ValueError) as e:
        raise ValueError(
            f"Aborting, could not load a CA from {ca_pem_file}: {e}. The file has to contain "
            "both the CA certificate and its unencrypted private key, just like the agent CA it "
            "replaces."
        )

    if (violation := _agent_ca_requirement_violation(ca.certificate)) is not None:
        raise ValueError(f"Aborting, the CA in {ca_pem_file} cannot be used because {violation}.")

    return RootCA(certificate=ca.certificate, private_key=ca.private_key)


def _verify_common_name(
    provided_certificate: Certificate, current_certificate: Certificate, force: bool
) -> None:
    """Verify that a provided CA can authorize the already registered agents.

    The agent receiver authorizes agents by the common name of their certificate's issuer, so a
    different common name would lock out all agents until they are registered again. `force`
    performs the rotation regardless, accepting that lockout.
    """
    if (provided_cn := provided_certificate.common_name) == (
        expected_cn := current_certificate.common_name
    ):
        return

    if not force:
        raise ValueError(
            f'Aborting, the provided CA has the common name "{provided_cn}", but the agent '
            f"receiver only accepts agents whose certificate was issued by a CA with the common "
            f"name '{expected_cn}'. Rotating to it would lock out all registered agents.\n"
            "Use --force to rotate to it anyway and register all agents again afterwards."
        )

    sys.stdout.write(
        f'cmk-cert: WARNING: The provided CA has the common name "{provided_cn}" instead of '
        f"'{expected_cn}'. The agent receiver will reject all currently registered agents, "
        "they have to be registered again.\n"
    )


def _reload_agent_receiver() -> None:
    """Reload the agent receiver, which rebuilds the trusted certificate store on startup."""
    completed_process = subprocess.run(
        ["omd", "reload", "agent-receiver"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        shell=False,
        encoding="utf-8",
        check=False,
    )
    logger.log(
        logging.DEBUG if completed_process.returncode == 0 else logging.WARNING,
        "'omd reload agent-receiver' finished. Exit code: %(returncode)s, Output: %(output)s",
        {"returncode": completed_process.returncode, "output": completed_process.stdout},
    )

    if completed_process.returncode:
        raise RuntimeError(f"Failed to reload the agent receiver:\n{completed_process.stdout}")


def rotate_agent_ca_certificate(
    omd_root: Path,
    site_id: SiteId,
    expiry: int | None = None,
    key_size: int = 4096,
    ca_pem: Path | None = None,
    force: bool = False,
) -> None:
    """Rotate the agent signing CA certificate.

    The current CA is renamed and stays trusted, so that the certificates it issued keep working.
    It is replaced by a newly generated CA or by the one provided in `ca_pem`.
    """
    expiry_ = _days_until_10_years_from_today() if expiry is None else expiry

    ca_path = agent_root_ca_path(site_root_dir=omd_root)
    retired_ca_path = ca_path.with_name(f"{date.today().isoformat()}_ca_old.pem")
    if retired_ca_path.exists():
        free_path = retired_ca_path
        count = 1
        while free_path.exists():
            count += 1
            free_path = retired_ca_path.with_name(f"{retired_ca_path.stem}_{count}.pem")
        raise ValueError(
            f"Aborting, the agent CA has already been rotated today: {retired_ca_path} exists and "
            "would be overwritten, which would lock out the agents still using it.\n"
            "To rotate again today, move it aside first. Keep it in the same directory with a "
            "'.pem' suffix, so that it stays trusted:\n"
            f"  mv {retired_ca_path} {free_path}\n"
        )

    # Validate a provided CA before touching the current one
    provided_ca = None if ca_pem is None else _load_provided_agent_ca(ca_pem)
    if provided_ca is not None:
        _verify_common_name(
            provided_ca.certificate,
            Certificate.load_pem(CertificatePEM(ca_path.read_bytes())),
            force,
        )

    # Generate first, swap later, so a failure leaves the current CA in place. The temporary
    # name must not end in '.pem', or the agent receiver would already trust it.
    new_ca_path = ca_path.with_name(f"{ca_path.name}.new")
    if provided_ca is None:
        new_ca = RootCA.create(
            path=new_ca_path,
            name=f"Site '{site_id}' agent signing CA",
            validity=relativedelta(days=expiry_),
            key_size=key_size,
        )
    else:
        new_ca = provided_ca
        new_ca_path.write_bytes(
            new_ca.private_key.dump_pem(password=None).bytes + new_ca.certificate.dump_pem().bytes
        )
        new_ca_path.chmod(mode=0o660)

    shutil.move(ca_path, retired_ca_path)
    new_ca_path.replace(ca_path)

    log_security_event(
        CertManagementEvent(
            event="certificate rotated",
            component="agent certificate authority",
            actor="cmk-cert",
            cert=new_ca.certificate,
        )
    )

    _reload_agent_receiver()

    sys.stdout.write(
        "cmk-cert: Agent signing CA certificate rotation successfully finished.\n"
        f"The previous CA is kept at {retired_ca_path} and stays trusted, so that agents "
        "registered with it keep working until they have renewed their certificate.\n"
        "Once no agent uses a certificate issued by the previous CA anymore, remove it with:\n"
        f"  rm {retired_ca_path}\n"
        "  omd reload agent-receiver\n"
    )

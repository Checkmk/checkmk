#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from tests.testlib.site import Site


def _read_fingerprint(site: Site, cert: Path) -> str:
    assert site.file_exists(str(cert)), f"Certificate file {cert} does not exist"
    fp = site.check_output(["openssl", "x509", "-in", str(cert), "-noout", "-fingerprint"]).strip()

    assert isinstance(fp, str)
    assert fp.startswith("SHA1 Fingerprint="), f"Failed to read fingerprint of certificate {cert}"

    return fp


def test_rotate_site_certificate(central_site: Site) -> None:
    old_fingerprint = _read_fingerprint(central_site, Path(f"etc/ssl/sites/{central_site.id}.pem"))

    central_site.check_output(["cmk-cert", "rotate", "site"])

    assert old_fingerprint != _read_fingerprint(
        central_site, Path(f"etc/ssl/sites/{central_site.id}.pem")
    ), "Site certificate fingerprint did not change"


def test_rotate_central_site_ca(central_site: Site) -> None:
    """
    Test rotation of the central site CA certificate:
     - initiate rotation with `cmk-cert rotate site-ca`
     - activate changes and wait for site restart
     - finalize rotation with `cmk-cert rotate site-ca --finalize`
     - verify that the CA certificate fingerprint has changed
    """

    assert not central_site.file_exists("etc/ssl/pending_certificate_rotation"), (
        "Found unexpected pending_certificate_rotation directory before CA rotation"
    )
    old_fingerprint = _read_fingerprint(central_site, Path("etc/ssl/ca.pem"))

    central_site.check_output(["cmk-cert", "rotate", "site-ca"])

    assert central_site.file_exists("etc/ssl/pending_certificate_rotation"), (
        "Expected pending_certificate_rotation directory after CA rotation"
    )
    assert _read_fingerprint(central_site, Path("etc/ssl/ca.pem")) == old_fingerprint, (
        "Central site CA certificate fingerprint changed before activation"
    )
    assert central_site.openapi.changes.get_pending(), "Expected pending changes after CA rotation"

    central_site.openapi.changes.activate_and_wait_for_completion(sites=[central_site.id])
    central_site.check_output(["cmk-cert", "rotate", "site-ca", "--finalize"])

    assert old_fingerprint != _read_fingerprint(central_site, Path("etc/ssl/ca.pem")), (
        "Central site CA certificate fingerprint did not change"
    )


def _get_trusted_ca_certs(site: Site) -> list[str]:
    trusted_certificate_authorities = site.read_global_settings(
        Path("etc/check_mk/multisite.d/wato/ca-certificates.mk")
    ).get("trusted_certificate_authorities", {})
    assert isinstance(trusted_certificate_authorities, dict)

    trusted_cas = trusted_certificate_authorities.get("trusted_cas", [])
    assert isinstance(trusted_cas, list)
    return trusted_cas


def test_rotate_remote_site_ca(central_site: Site, remote_site: Site) -> None:
    """
    Test rotation of a remote site CA certificate:
     - `cmk-cert rotate site-ca --remote-site REMOTE` on central
     - activate all sites' changes
     - `cmk-cert rotate site-ca --remote-site REMOTE --finalize`
     - verify that the CA certificate fingerprint has changed
    """

    old_ca_fingerprint = _read_fingerprint(remote_site, Path("etc/ssl/ca.pem"))
    old_site_cert_fingerprint = _read_fingerprint(
        remote_site, Path(f"etc/ssl/sites/{remote_site.id}.pem")
    )
    old_trusted_certs = _get_trusted_ca_certs(central_site)

    # - initialize rotation -
    #
    central_site.check_output(["cmk-cert", "rotate", "site-ca", "--remote-site", remote_site.id])

    assert central_site.file_exists("etc/ssl/pending_certificate_rotation/state.json"), (
        # state of ongoing rotation is tracked on central site
        "Expected state file for pending certificate rotation on central site"
    )
    assert remote_site.file_exists("etc/ssl/temp_certificate/ca.pem"), (
        # new CA certificate is staged in temp_certificate on remote site
        "Expected new CA file in temp_certificate directory on remote site"
    )
    assert _read_fingerprint(remote_site, Path("etc/ssl/ca.pem")) == old_ca_fingerprint, (
        "Remote site CA certificate fingerprint changed before activation"
    )
    assert central_site.openapi.changes.get_pending(), "Expected pending changes after CA rotation"

    # - activate changes and finalize rotation -
    #
    central_site.openapi.changes.activate_and_wait_for_completion(
        sites=[central_site.id, remote_site.id]
    )
    central_site.check_output(
        ["cmk-cert", "rotate", "site-ca", "--remote-site", remote_site.id, "--finalize"]
    )

    assert old_ca_fingerprint != _read_fingerprint(remote_site, Path("etc/ssl/ca.pem")), (
        "Remote site CA certificate fingerprint did not change"
    )
    assert old_site_cert_fingerprint != _read_fingerprint(
        remote_site, Path(f"etc/ssl/sites/{remote_site.id}.pem")
    ), "Remote site site certificate fingerprint did not change"

    new_trusted_certs = _get_trusted_ca_certs(central_site)
    assert len(new_trusted_certs) == 1 + len(old_trusted_certs), (
        "Central site trusted CA certificates not updated after remote site CA rotation"
    )

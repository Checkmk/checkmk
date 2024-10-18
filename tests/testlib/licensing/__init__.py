#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest

from tests.testlib.licensing.cee.key_or_cert import licensing_key_or_cert, LicensingKeyOrCert
from tests.testlib.licensing.cee.license_files import create_verification_response
from tests.testlib.site import Site
from tests.testlib.utils import run, write_file

from cmk.ccc.version import Edition

from cmk.utils.cee.licensing.export import (
    make_cee_parser,
    RawAdditionalFeature,
    RawAdditionalLimitFeature,
    RawSubscriptionData,
    UploadOrigin,
    VerificationRequest,
    VerificationResponse,
)
from cmk.utils.licensing.export import LicensingProtocolVersion

logger = logging.getLogger(__name__)


@contextmanager
def ca_certificate(site: Site) -> Iterator[LicensingKeyOrCert]:
    """Update CA certificate (create a backup of the original certificate)"""
    ca_cert_file = Path(site.root) / "share" / "check_mk" / "licensing" / "ca-certificate.pem"
    ca_cert_backup = Path(site.root) / f"{ca_cert_file.name}.bak"
    # NOTE: The certificate is owned by root!
    restore_backup = (
        run(
            ["cp", ca_cert_file.as_posix(), ca_cert_backup.as_posix()], check=False, sudo=True
        ).returncode
        == 0
    ) and os.getenv("CLEANUP", "1") == "1"
    try:
        key_or_cert = licensing_key_or_cert()
        write_file(ca_cert_file, key_or_cert.certificate.dump_pem().bytes, sudo=True)
        yield key_or_cert
    finally:
        if restore_backup:
            run(["cp", ca_cert_backup.as_posix(), ca_cert_file.as_posix()], sudo=True)


@contextmanager
def site_license_request(site: Site) -> Iterator[VerificationRequest]:
    """Prepare the verification request file and yield the verification request."""
    verification_request_file = site.licensing_dir / "verification_request_id"
    site.write_text_file(verification_request_file, "")
    created_at = int(time.time())
    raw_verification_request = {
        "VERSION": LicensingProtocolVersion,
        "request_id": str(uuid4()),
        "instance_id": str(uuid4()),
        "created_at": created_at,
        "upload_origin": UploadOrigin.from_checkmk.name,
        "history": [],
    }
    verification_request = make_cee_parser(LicensingProtocolVersion).parse_verification_request(
        raw_verification_request
    )
    verification_request_text = json.dumps(verification_request.for_report(), indent=4)
    site.write_text_file(verification_request_file, verification_request_text)
    try:
        yield verification_request
    finally:
        if os.getenv("CLEANUP", "1") == "1":
            site.delete_file(verification_request_file)


@contextmanager
def site_license_response(site: Site) -> Iterator[Path]:
    """Prepare the verification response file and yield the path."""
    verification_response_file = site.licensing_dir / "verification_response"
    site.write_text_file(verification_response_file, "")
    try:
        yield verification_response_file
    finally:
        if os.getenv("CLEANUP", "1") == "1":
            site.delete_file(verification_response_file)


@contextmanager
def license_site(
    site: Site,
    edition: Edition | None = None,
    license_start_offset_seconds: int = 0,
    license_validity_days: int = 90,
    service_limit: int = -1,
) -> Iterator[tuple[VerificationRequest, VerificationResponse]]:
    edition = edition or site.version.edition
    if edition == Edition.CRE:
        pytest.skip(f"License testing is not supported for {edition.title}!")

    with (
        ca_certificate(site) as ca_cert,
        site_license_request(site) as verification_request,
        site_license_response(site) as verification_response_file,
    ):
        # Serialize and store the verification response
        verification_response = create_verification_response(
            private_key=ca_cert.private_key,
            certificate=ca_cert.certificate,
            raw_subscription_data=RawSubscriptionData(
                group_and_managed_services_use=False,
                reseller_name="",
                checkmk_edition=edition.short,
                checkmk_max_version="",
                subscription_start_ts=(start_ts := int(time.time()) + license_start_offset_seconds),
                subscription_expiration_ts=start_ts + 86400 * license_validity_days,
                subscription_auto_renewal=False,
                operational_state="active",
                service_limit=service_limit,
                unbound_license=True,
                additional_features=[
                    RawAdditionalFeature(name="ntop", enabled=False),
                    RawAdditionalFeature(name="virt1_appliance", enabled=False),
                    RawAdditionalLimitFeature(name="synthetic_monitoring", enabled=True, limit=100),
                ],
            ),
            request_id=verification_request.request_id,
        )
        verification_response_text = json.dumps(
            verification_response.for_report(),
            indent=4,
        )
        site.write_text_file(verification_response_file, verification_response_text)
        site.restart_core()

        yield verification_request, verification_response

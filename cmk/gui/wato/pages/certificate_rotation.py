#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from dateutil.relativedelta import relativedelta

import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.watolib.automation_commands import AutomationCommand, AutomationCommandRegistry
from cmk.utils.certs import cert_dir, CertManagementEvent, SiteCA
from cmk.utils.log.security_event import log_security_event

SITE_CA_CERTIFICATE_DIRECTORY = cert_dir(cmk.utils.paths.omd_root)
SITE_CA_CERTIFICATE_TMP_PATH = SITE_CA_CERTIFICATE_DIRECTORY / "temp_certificate"
TEMPORARY_CA_FILE_PATH = Path(SITE_CA_CERTIFICATE_TMP_PATH / "ca.pem")


def register(automation_command_registry: AutomationCommandRegistry) -> None:
    automation_command_registry.register(AutomationStageSiteCACertificateRotation)
    automation_command_registry.register(AutomationFinalizeSiteCACertificateRotation)
    automation_command_registry.register(AutomationSiteCertificateRotation)


@dataclass
class CertificateRotationParameters:
    site_id: str
    additional_sans: Sequence[str]
    expiry: int
    key_size: int

    @classmethod
    def from_request(cls, config: Config, request: Request) -> "CertificateRotationParameters":
        return cls(
            site_id=request.get_str_input_mandatory("site_id"),
            additional_sans=config.site_subject_alternative_names,
            expiry=request.get_integer_input_mandatory("expiry"),
            key_size=request.get_integer_input_mandatory("key_size"),
        )


class AutomationStageSiteCACertificateRotation(AutomationCommand[CertificateRotationParameters]):
    def command_name(self) -> str:
        return "stage-site-ca-certificate-rotation"

    def execute(self, api_request: CertificateRotationParameters) -> str:
        site_ca = _stage_site_ca_certificate_rotation(
            site_id=api_request.site_id,
            expiry=api_request.expiry,
            key_size=api_request.key_size,
        )
        return site_ca.root_ca.certificate.dump_pem().bytes.decode("utf-8")

    def get_request(self, config: Config, request: Request) -> CertificateRotationParameters:
        return CertificateRotationParameters.from_request(config, request)


def _stage_site_ca_certificate_rotation(site_id: str, expiry: int, key_size: int) -> SiteCA:
    site_ca = SiteCA.create(
        cert_dir=Path(SITE_CA_CERTIFICATE_TMP_PATH),
        site_id=SiteId(site_id),
        expiry=relativedelta(days=expiry),
        key_size=key_size,
    )
    return site_ca


class AutomationFinalizeSiteCACertificateRotation(AutomationCommand[CertificateRotationParameters]):
    def command_name(self) -> str:
        return "finalize-site-ca-certificate-rotation"

    def execute(self, api_request: CertificateRotationParameters) -> str:
        return self._finalize_site_ca_certificate_rotation(
            site_id=SiteId(api_request.site_id),
            additional_sans=api_request.additional_sans,
            expiry=relativedelta(days=api_request.expiry),
            key_size=api_request.key_size,
        )

    def get_request(self, config: Config, request: Request) -> CertificateRotationParameters:
        return CertificateRotationParameters.from_request(config, request)

    @staticmethod
    def _finalize_site_ca_certificate_rotation(
        site_id: SiteId,
        additional_sans: Sequence[str],
        expiry: relativedelta,
        key_size: int,
    ) -> str:
        site_ca = SiteCA.load(certificate_directory=SITE_CA_CERTIFICATE_TMP_PATH)

        shutil.move(TEMPORARY_CA_FILE_PATH, Path(SITE_CA_CERTIFICATE_DIRECTORY / "ca.pem"))

        site_ca.cert_dir = SITE_CA_CERTIFICATE_DIRECTORY
        site_ca.create_site_certificate(
            site_id=site_id,
            additional_sans=additional_sans,
            expiry=expiry,
            key_size=key_size,
        )

        site_cert = SiteCA.load_site_certificate(SITE_CA_CERTIFICATE_DIRECTORY, site_id)

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

        shutil.rmtree(SITE_CA_CERTIFICATE_TMP_PATH, ignore_errors=True)

        return "success"


class AutomationSiteCertificateRotation(AutomationCommand[CertificateRotationParameters]):
    def command_name(self) -> str:
        return "site-certificate-rotation"

    def execute(self, api_request: CertificateRotationParameters) -> str:
        try:
            self.rotate_local_site_certificate(
                SITE_CA_CERTIFICATE_DIRECTORY,
                SiteId(api_request.site_id),
                api_request.additional_sans,
                api_request.expiry,
                api_request.key_size,
            )
        except Exception as e:
            return f"failure: {e}"

        return "success"

    def get_request(self, config: Config, request: Request) -> CertificateRotationParameters:
        return CertificateRotationParameters.from_request(config, request)

    @staticmethod
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

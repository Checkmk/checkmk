#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass, fields
from enum import auto, StrEnum
from pathlib import Path

from cmk.ccc.version import Edition

from .verification import CheckmkEdition as LicensedEdition
from .verification import load_plain_verification_response


@dataclass(frozen=True)
class LicenseFlag:
    enabled: bool


class OptionName(StrEnum):
    BAKERY = auto()
    TELEMETRY = auto()
    OTEL_COLLECTOR = auto()


@dataclass(frozen=True)
class LicenseOptions:
    bakery: LicenseFlag
    telemetry: LicenseFlag
    otel_collector: LicenseFlag

    def get_flag(self, name: OptionName) -> LicenseFlag:
        match name:
            case OptionName.BAKERY:
                return self.bakery
            case OptionName.TELEMETRY:
                return self.telemetry
            case OptionName.OTEL_COLLECTOR:
                return self.otel_collector

    def disabled(self) -> set[str]:
        return {f.name for f in fields(self) if not getattr(self, f.name).enabled}


def get_license_options(omd_root: Path, edition: Edition) -> LicenseOptions:
    licensed = load_plain_verification_response(omd_root)
    match edition:
        case Edition.COMMUNITY:
            # community edition -> all features disabled.
            return LicenseOptions(
                bakery=LicenseFlag(enabled=False),
                telemetry=LicenseFlag(enabled=False),
                otel_collector=LicenseFlag(enabled=False),
            )

        case Edition.PRO:
            return _make_pro_options()

        case Edition.ULTIMATE:
            if licensed and licensed.checkmk_edition is LicensedEdition.cee:
                # WIP: behave like a PRO.
                return _make_pro_options()
            # no license -> all features enabled. We must assume TRIAL.
            return LicenseOptions(
                bakery=LicenseFlag(enabled=True),
                telemetry=LicenseFlag(enabled=True),
                otel_collector=LicenseFlag(enabled=True),
            )

        case Edition.ULTIMATEMT:
            return LicenseOptions(
                bakery=LicenseFlag(enabled=True),
                telemetry=LicenseFlag(enabled=True),
                otel_collector=LicenseFlag(enabled=True),
            )

        case Edition.CLOUD:
            return LicenseOptions(
                bakery=LicenseFlag(enabled=True),
                telemetry=LicenseFlag(enabled=True),
                otel_collector=LicenseFlag(enabled=True),
            )


def _make_pro_options() -> LicenseOptions:
    return LicenseOptions(
        bakery=LicenseFlag(enabled=True),
        telemetry=LicenseFlag(enabled=False),
        otel_collector=LicenseFlag(enabled=False),
    )

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
class FeatureFlag:
    enabled: bool


class FeatureName(StrEnum):
    BAKERY = auto()


@dataclass(frozen=True)
class Features:
    bakery: FeatureFlag

    def get_flag(self, name: FeatureName) -> FeatureFlag:
        match name:
            case FeatureName.BAKERY:
                return self.bakery

    def disabled(self) -> set[str]:
        return {f.name for f in fields(self) if not getattr(self, f.name).enabled}


# NOTE: Soon this will consider the contents of the actual license.
def licensed_features(omd_root: Path, edition: Edition) -> Features:
    if edition is Edition.COMMUNITY:
        # community edition -> all features disabled.
        return Features(bakery=FeatureFlag(enabled=False))

    if (response := load_plain_verification_response(omd_root)) is None:
        # no license -> all features enabled. We must assume TRIAL.
        return Features(bakery=FeatureFlag(enabled=True))

    if edition is Edition.ULTIMATE and response.checkmk_edition is LicensedEdition.cee:
        # WIP: behave like a PRO.
        return Features(bakery=FeatureFlag(enabled=True))

    return Features(bakery=FeatureFlag(enabled=True))

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.ccc.version import Edition

from .handler import LicensingHandler


@dataclass(frozen=True)
class FeatureFlag:
    enabled: bool


@dataclass(frozen=True)
class Features:
    bakery: FeatureFlag


# NOTE: This will become significantly more complex soon.
# In particular: this information depends on the contents of
# the actual license.
# This is only added as a very first step, to decouple
# different implementation aspects.
def licensed_features(
    edition: Edition,
    licensing_handler: LicensingHandler,  # noqa: ARG001
) -> Features:
    return Features(bakery=FeatureFlag(enabled=edition is not Edition.COMMUNITY))

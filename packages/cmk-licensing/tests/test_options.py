#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.version import Edition
from cmk.licensing.basics.options import get_license_options, LicenseFlag, LicenseOptions


def test_community() -> None:
    assert get_license_options(Path(), Edition.COMMUNITY) == LicenseOptions(
        bakery=LicenseFlag(enabled=False),
        telemetry=LicenseFlag(enabled=False),
        otel_collector=LicenseFlag(enabled=False),
        aws_extended=LicenseFlag(enabled=False),
    )


def test_pro() -> None:
    assert get_license_options(Path(), Edition.PRO) == LicenseOptions(
        bakery=LicenseFlag(enabled=True),
        telemetry=LicenseFlag(enabled=False),
        otel_collector=LicenseFlag(enabled=False),
        aws_extended=LicenseFlag(enabled=False),
    )


@pytest.mark.parametrize(
    "edition",
    [e for e in Edition if e not in [Edition.COMMUNITY, Edition.PRO]],
)
def test_commercial(edition: Edition) -> None:
    assert get_license_options(Path(), edition) == LicenseOptions(
        bakery=LicenseFlag(enabled=True),
        telemetry=LicenseFlag(enabled=True),
        otel_collector=LicenseFlag(enabled=True),
        aws_extended=LicenseFlag(enabled=True),
    )

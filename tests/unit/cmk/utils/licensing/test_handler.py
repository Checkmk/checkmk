#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.licensing.handler import LicenseState


@pytest.mark.parametrize(
    "license_state, expected_readable",
    [
        (LicenseState.TRIAL, "trial"),
        (LicenseState.FREE, "free"),
        (LicenseState.LICENSED, "licensed"),
        (LicenseState.UNLICENSED, "unlicensed"),
    ],
)
def test_license_state_readable(license_state: LicenseState, expected_readable: str) -> None:
    assert license_state.readable == expected_readable

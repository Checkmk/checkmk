# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.watolib import wire_format
from cmk.licensing.handler import LicenseState


def test_license_state_to_ping_string() -> None:
    assert wire_format.license_state_to_ping_string(LicenseState.FREE) == "FREE"
    assert wire_format.license_state_to_ping_string(LicenseState.TRIAL) == "TRIAL"
    assert (
        wire_format.license_state_to_ping_string(LicenseState.PENDING_TRIAL_VERIFICATION) == "TRIAL"
    )
    assert (
        wire_format.license_state_to_ping_string(LicenseState.PENDING_LICENSE_VERIFICATION)
        == "TRIAL"
    )
    assert wire_format.license_state_to_ping_string(LicenseState.PENDING_SELECTION) == "TRIAL"
    assert wire_format.license_state_to_ping_string(LicenseState.LICENSED) == "LICENSED"
    assert wire_format.license_state_to_ping_string(LicenseState.UNLICENSED) == "UNLICENSED"


def test_license_state_from_ping_string() -> None:
    assert wire_format.license_state_from_ping_string("FREE") is LicenseState.FREE
    assert wire_format.license_state_from_ping_string("TRIAL") is LicenseState.TRIAL
    assert wire_format.license_state_from_ping_string("LICENSED") is LicenseState.LICENSED
    assert wire_format.license_state_from_ping_string("UNLICENSED") is LicenseState.UNLICENSED
    assert wire_format.license_state_from_ping_string("") is None
    assert wire_format.license_state_from_ping_string("_INVALID_STATE") is None

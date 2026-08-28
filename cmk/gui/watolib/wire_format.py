# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Utilities related to the automation protocol wire format.

This module will be shared between the automation code in the central and remote sites.
"""

from typing import Literal

from cmk.licensing.handler import LicenseState

LicenseWireString = Literal["TRIAL", "FREE", "LICENSED", "UNLICENSED"]


def license_state_to_ping_string(license_state: LicenseState) -> LicenseWireString:
    """Converts a license state to the string used in a Ping automation.

    This may not cover all possible license states because of backwards compatibility.
    """

    # The enum constants may change at any point. Since the string is part of the automation
    # protocol, it needs to stay stable for backwards compatibility. This match statement will
    # convert the enums to the original set of four supported license states as best as possible. In
    # the future we may add support for the new license states as well, but that would require
    # releasing parsing and emitting of new values in different Checkmk releases. See CMK-38586 for
    # the pending support for the new license states that will be added to support trial tracking.
    match license_state:
        case LicenseState.TRIAL:
            return "TRIAL"
        case LicenseState.FREE:
            return "FREE"
        case LicenseState.LICENSED:
            return "LICENSED"
        case LicenseState.UNLICENSED:
            return "UNLICENSED"


def _wire_string_to_license_state(wire_string: LicenseWireString) -> LicenseState:
    match wire_string:
        case "TRIAL":
            return LicenseState.TRIAL
        case "FREE":
            return LicenseState.FREE
        case "LICENSED":
            return LicenseState.LICENSED
        case "UNLICENSED":
            return LicenseState.UNLICENSED


def license_state_from_ping_string(raw_license_state: str) -> LicenseState | None:
    """Converts a license state present in a Ping automation to the enum.

    The inverse of license_state_to_ping_string().
    """

    # See comments in license_state_to_ping_string.
    match raw_license_state:
        case "TRIAL" | "FREE" | "LICENSED" | "UNLICENSED":
            return _wire_string_to_license_state(raw_license_state)
        case _:
            return None

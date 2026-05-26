#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import all_of, any_of, matches, startswith, State

DETECT = all_of(
    any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2620"),
        matches(".1.3.6.1.2.1.1.1.0", "[^ ]+ [^ ]+ [^ ]*cp( .*)?"),
        startswith(".1.3.6.1.2.1.1.1.0", "IPSO "),
        matches(".1.3.6.1.2.1.1.1.0", "Linux.*cpx.*"),
    ),
    any_of(
        startswith(".1.3.6.1.4.1.2620.1.1.21.0", "firewall"),
        matches(".1.3.6.1.4.1.2620.1.6.5.1.0", "Gaia"),
    ),
)

SENSOR_STATUS_TO_CMK_STATUS: Mapping[str, tuple[State, str]] = {
    "0": (State.OK, "sensor in range"),
    "1": (State.CRIT, "sensor out of range"),
    "2": (State.UNKNOWN, "reading error"),
}

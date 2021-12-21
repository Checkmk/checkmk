#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Final


def scan_cisco_ucs(oid) -> bool:
    return (
        ".1.3.6.1.4.1.9.1.1682" in oid(".1.3.6.1.2.1.1.2.0")
        or ".1.3.6.1.4.1.9.1.1683" in oid(".1.3.6.1.2.1.1.2.0")
        or ".1.3.6.1.4.1.9.1.1684" in oid(".1.3.6.1.2.1.1.2.0")
        or ".1.3.6.1.4.1.9.1.1685" in oid(".1.3.6.1.2.1.1.2.0")
        or ".1.3.6.1.4.1.9.1.2178" in oid(".1.3.6.1.2.1.1.2.0")
        or ".1.3.6.1.4.1.9.1.2424" in oid(".1.3.6.1.2.1.1.2.0")
        or ".1.3.6.1.4.1.9.1.2492" in oid(".1.3.6.1.2.1.1.2.0")
        or ".1.3.6.1.4.1.9.1.2493" in oid(".1.3.6.1.2.1.1.2.0")
    )


map_operability: Final = {
    "0": (2, "unknown"),
    "1": (0, "operable"),
    "2": (2, "inoperable"),
    "3": (2, "degraded"),
    "4": (1, "poweredOff"),
    "5": (2, "powerProblem"),
    "6": (0, "removed"),
    "7": (2, "voltageProblem"),
    "8": (2, "thermalProblem"),
    "9": (1, "performanceProblem"),
    "10": (1, "accessibilityProblem"),
    "11": (1, "identityUnestablishable"),
    "12": (2, "biosPostTimeout"),
    "13": (1, "disabled"),
    "14": (1, "malformedFru"),
    "51": (1, "fabricConnProblem"),
    "52": (1, "fabricUnsupportedConn"),
    "81": (1, "config"),
    "82": (2, "equipmentProblem"),
    "83": (2, "decomissioning"),
    "84": (1, "chassisLimitExceeded"),
    "100": (1, "notSupported"),
    "101": (1, "discovery"),
    "102": (2, "discoveryFailed"),
    "103": (1, "identify"),
    "104": (2, "postFailure"),
    "105": (1, "upgradeProblem"),
    "106": (1, "peerCommProblem"),
    "107": (0, "autoUpgrade"),
    "108": (1, "linkActivateBlocked"),
}

map_presence: Final = {
    "0": (1, "unknown"),
    "1": (0, "empty"),
    "10": (0, "equipped"),
    "11": (0, "missing"),
    "12": (1, "mismatch"),
    "13": (0, "equippedNotPrimary"),
    "14": (0, "equippedSlave"),
    "15": (1, "mismatchSlave"),
    "16": (1, "missingSlave"),
    "20": (1, "equippedIdentityUnestablishable"),
    "21": (1, "mismatchIdentityUnestablishable"),
    "22": (1, "equippedWithMalformedFru"),
    "30": (1, "inaccessible"),
    "40": (1, "unauthorized"),
    "100": (1, "notSupported"),
    "101": (1, "equippedUnsupported"),
    "102": (1, "equippedDiscNotStarted"),
    "103": (0, "equippedDiscInProgress"),
    "104": (2, "equippedDiscError"),
    "105": (1, "equippedDiscUnknown"),
}

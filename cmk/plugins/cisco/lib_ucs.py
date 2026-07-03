#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import assert_never, Final, Literal

from cmk.agent_based.v2 import any_of, CheckResult, contains, exists, Result, State

DETECT = any_of(
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1682"),
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1683"),
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1684"),
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1685"),
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2178"),
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2179"),
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2424"),
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2492"),
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2493"),
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.3100"),
    # Standalone Cisco IMC (CIMC) appliances and newer UCS C-series models --
    # e.g. SNS-8355-K9 / UCS C225 M8 -- report a sysObjectID that is not on the
    # whitelist above, so none of the cisco_ucs_* services were discovered even
    # though the device fully serves the CISCO-UNIFIED-COMPUTING-MIB. Match any
    # device that exposes the UCS compute rack-unit operability column
    # (cucsComputeRackUnitOperability) as well.
    exists(".1.3.6.1.4.1.9.9.719.1.9.35.1.43.*"),
)


MAP_OPERABILITY: Final[Mapping[str, tuple[Literal[0, 1, 2], str]]] = {
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

MAP_PRESENCE: Final[Mapping[str, tuple[Literal[0, 1, 2], str]]] = {
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
}


class Operability(Enum):
    unknown = "0"
    operable = "1"
    inoperable = "2"
    degraded = "3"
    poweredOff = "4"
    powerProblem = "5"
    removed = "6"
    voltageProblem = "7"
    thermalProblem = "8"
    performanceProblem = "9"
    accessibilityProblem = "10"
    identityUnestablishable = "11"
    biosPostTimeout = "12"
    disabled = "13"
    malformedFru = "14"
    fabricConnProblem = "51"
    fabricUnsupportedConn = "52"
    config = "81"
    equipmentProblem = "82"
    decomissioning = "83"
    chassisLimitExceeded = "84"
    notSupported = "100"
    discovery = "101"
    discoveryFailed = "102"
    identify = "103"
    postFailure = "104"
    upgradeProblem = "105"
    peerCommProblem = "106"
    autoUpgrade = "107"
    linkActivateBlocked = "108"

    def monitoring_state(self) -> State:
        match self:
            case Operability.unknown:
                return State.CRIT
            case Operability.operable:
                return State.OK
            case Operability.inoperable:
                return State.CRIT
            case Operability.degraded:
                return State.CRIT
            case Operability.poweredOff:
                return State.WARN
            case Operability.powerProblem:
                return State.CRIT
            case Operability.removed:
                return State.OK
            case Operability.voltageProblem:
                return State.CRIT
            case Operability.thermalProblem:
                return State.CRIT
            case Operability.performanceProblem:
                return State.WARN
            case Operability.accessibilityProblem:
                return State.WARN
            case Operability.identityUnestablishable:
                return State.WARN
            case Operability.biosPostTimeout:
                return State.CRIT
            case Operability.disabled:
                return State.WARN
            case Operability.malformedFru:
                return State.WARN
            case Operability.fabricConnProblem:
                return State.WARN
            case Operability.fabricUnsupportedConn:
                return State.WARN
            case Operability.config:
                return State.WARN
            case Operability.equipmentProblem:
                return State.CRIT
            case Operability.decomissioning:
                return State.CRIT
            case Operability.chassisLimitExceeded:
                return State.WARN
            case Operability.notSupported:
                return State.WARN
            case Operability.discovery:
                return State.WARN
            case Operability.discoveryFailed:
                return State.CRIT
            case Operability.identify:
                return State.WARN
            case Operability.postFailure:
                return State.CRIT
            case Operability.upgradeProblem:
                return State.WARN
            case Operability.peerCommProblem:
                return State.WARN
            case Operability.autoUpgrade:
                return State.OK
            case Operability.linkActivateBlocked:
                return State.WARN
            case _:
                assert_never(self)


class Presence(Enum):
    unknown = "0"
    empty = "1"
    equipped = "10"
    missing = "11"
    mismatch = "12"
    equippedNotPrimary = "13"
    equippedSlave = "14"
    mismatchSlave = "15"
    missingSlave = "16"
    equippedIdentityUnestablishable = "20"
    mismatchIdentityUnestablishable = "21"
    equippedWithMalformedFru = "22"
    inaccessible = "30"
    unauthorized = "40"
    notSupported = "100"
    equippedUnsupported = "101"
    equippedDiscNotStarted = "102"
    equippedDiscInProgress = "103"
    equippedDiscError = "104"
    equippedDiscUnknown = "105"

    def monitoring_state(self) -> State:
        match self:
            case Presence.unknown:
                return State.WARN
            case Presence.empty:
                return State.OK
            case Presence.equipped:
                return State.OK
            case Presence.missing:
                return State.OK
            case Presence.mismatch:
                return State.WARN
            case Presence.equippedNotPrimary:
                return State.OK
            case Presence.equippedSlave:
                return State.OK
            case Presence.mismatchSlave:
                return State.WARN
            case Presence.missingSlave:
                return State.WARN
            case Presence.equippedIdentityUnestablishable:
                return State.WARN
            case Presence.mismatchIdentityUnestablishable:
                return State.WARN
            case Presence.equippedWithMalformedFru:
                return State.WARN
            case Presence.inaccessible:
                return State.WARN
            case Presence.unauthorized:
                return State.WARN
            case Presence.notSupported:
                return State.WARN
            case Presence.equippedUnsupported:
                return State.WARN
            case Presence.equippedDiscNotStarted:
                return State.WARN
            case Presence.equippedDiscInProgress:
                return State.OK
            case Presence.equippedDiscError:
                return State.CRIT
            case Presence.equippedDiscUnknown:
                return State.WARN
            case _:
                assert_never(self)


class FaultSeverity(Enum):
    cleared = "0"
    info = "1"
    warning = "3"
    minor = "4"
    major = "5"
    critical = "6"


@dataclass(frozen=True, kw_only=True)
class Fault:
    acknowledge: bool
    code: str
    description: str
    severity: FaultSeverity

    def monitoring_state(self) -> State:
        # refererence: werk #17287
        # if self.acknowledge:
        #     return State.OK

        match self.severity:
            case FaultSeverity.major | FaultSeverity.critical:
                return State.CRIT
            case FaultSeverity.warning | FaultSeverity.minor:
                return State.WARN
            case FaultSeverity.cleared | FaultSeverity.info:
                return State.OK
            case _:
                assert_never(self.severity)


def check_cisco_fault(faults: Sequence[Fault]) -> CheckResult:
    if faults:
        yield from (
            Result(
                state=fault.monitoring_state(),
                notice=f"Fault: {fault.code} - {fault.description}",
            )
            for fault in faults
        )
    else:
        yield Result(state=State.OK, notice="No faults")

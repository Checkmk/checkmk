#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="var-annotated"

from collections.abc import Mapping
from typing import Any, TypedDict

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import contains, OIDEnd, SNMPTree, StringTable


class ProtectorData(TypedDict, total=False):
    state: str
    current: float


check_info = {}

# Example for info:
# [[[u'1.1.1', u'4', u'0'],
#   [u'1.1.15', u'1', u'0'],
#   [u'1.2.1', u'4', u'0'],
#   [u'1.2.15', u'1', u'0'],
#   [u'1.3.1', u'4', u'70'],
#   [u'1.3.15', u'1', u'0'],
#   [u'1.4.1', u'4', u'0'],
#   [u'1.4.15', u'1', u'0'],
#   [u'1.5.1', u'4', u'0'],
#   [u'1.5.15', u'1', u'0'],
#   [u'1.6.1', u'4', u'0'],
#   [u'1.6.15', u'1', u'0']],
#  [[u'1'],
#   [u'0'],
#   [u'1'],
#   [u'0'],
#   [u'1'],
#   [u'0'],
#   [u'1'],
#   [u'0'],
#   [u'1'],
#   [u'0'],
#   [u'1'],
#   [u'0']]]
# Raritan implements a strange way of indexing here. The two last components
# of the OID should really be swapped!


def parse_raritan_pdu_ocprot(
    string_table: list[StringTable],
) -> dict[str, ProtectorData]:
    flattened_info = [
        [end_oid, state, value, scale]
        for (end_oid, state, value), (scale,) in zip(string_table[0], string_table[1])
    ]
    parsed = {}
    for end_oid, state, value, scale in flattened_info:
        protector_id = "C" + end_oid.split(".")[1]  # 1.5.1 --> Item will be "C5"

        if end_oid.endswith(".15"):
            parsed.setdefault(protector_id, {})["state"] = state
        elif end_oid.endswith(".1"):
            parsed.setdefault(protector_id, {})["current"] = float(value) / pow(10, int(scale))
    return parsed


def discover_raritan_pdu_ocprot(
    section: dict[str, ProtectorData],
) -> LegacyDiscoveryResult:
    yield from ((item, {}) for item in section)


def check_raritan_pdu_ocprot(
    item: str, params: Mapping[str, Any], parsed: dict[str, ProtectorData]
) -> LegacyCheckResult:
    if not (data := parsed.get(item)):
        return
    states = {
        "-1": (3, "Overcurrent protector information is unavailable"),
        "0": (2, "Overcurrent protector is open"),
        "1": (0, "Overcurrent protector is closed"),
    }
    if "state" in data:
        yield states[data["state"]]

    if "current" in data:
        yield check_levels(
            data["current"],
            "current",
            params["levels"],
            human_readable_func=lambda x: f"{x:.2f} A",
            infoname="Current",
        )


check_info["raritan_pdu_ocprot"] = LegacyCheckDefinition(
    name="raritan_pdu_ocprot",
    detect=contains(".1.3.6.1.2.1.1.2.0", "13742"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.5.3.3.1",
            oids=[OIDEnd(), "3", "4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.4.4.1",
            oids=["7"],
        ),
    ],
    parse_function=parse_raritan_pdu_ocprot,
    service_name="Overcurrent Protector %s",
    discovery_function=discover_raritan_pdu_ocprot,
    check_function=check_raritan_pdu_ocprot,
    check_ruleset_name="ocprot_current",
    check_default_parameters={"levels": (14.0, 15.0)},
)

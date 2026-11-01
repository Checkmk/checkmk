#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import ReadOnly, TypedDict

from pydantic import Field

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.raritan.lib import ParsedModel, PLUG_STATE_MAPPING


class PlugMeasurement(ParsedModel):
    """One aligned SNMP row, in fetch order; state codes are mapped afterwards."""

    index: str = Field(pattern=r"^\d+\.\d+$")
    outlet_label: str
    outlet_name: str
    switching_state: str


class Plug(ParsedModel):
    state: str
    outlet_name: str
    outlet_label: str


type Section = Mapping[str, Plug]


class CombinedParams(TypedDict, total=False):
    required_state: ReadOnly[str | None]
    discovered_state: ReadOnly[str]


def parse_raritan_pdu_plugs(string_table: StringTable) -> Section:
    measurements = [
        PlugMeasurement.model_validate(dict(zip(PlugMeasurement.model_fields, row, strict=True)))
        for row in string_table
    ]
    multiple_pdus = len({measurement.index.split(".")[0] for measurement in measurements}) > 1
    return {
        (measurement.index.replace(".", "/") if multiple_pdus else measurement.index.split(".")[1]): Plug(
            state=PLUG_STATE_MAPPING.get(measurement.switching_state, "unknown"),
            outlet_name=measurement.outlet_name,
            outlet_label=measurement.outlet_label,
        )
        for measurement in measurements
    }


def discover_raritan_pdu_plugs(section: Section) -> DiscoveryResult:
    for key, plug in section.items():
        if plug.state != "unknown":
            yield Service(item=key, parameters={"discovered_state": plug.state})


def check_raritan_pdu_plugs(item: str, params: CombinedParams, section: Section) -> CheckResult:
    if (plug := section.get(item)) is None:
        return

    if plug.outlet_name:
        yield Result(state=State.OK, summary=plug.outlet_name)
    if plug.outlet_label:
        yield Result(state=State.OK, summary=f"Label: {plug.outlet_label}")

    expected_state = params["required_state"] or params["discovered_state"]

    if plug.state != expected_state:
        yield Result(state=State.CRIT, summary=f"Status: {plug.state} (expected: {expected_state})")
    else:
        yield Result(state=State.OK, summary=f"Status: {plug.state}")


def _plug_tree() -> SNMPTree:
    """Fetch PDU2-MIB outlet labels, names and relay states for every PDU.

    Base: .1.3.6.1.4.1.13742.6.
    Outlet configuration entry: <base>.3.5.3.1.
    Outlet switch control entry: <base>.4.1.2.1.
    Each fetched column ends in .<pduId>.<outletId>.

    Checkmk joins the columns by their complete shared OID suffix. The fetch
    order matches PlugMeasurement.model_fields for zip() row mapping. Empty
    labels/names remain valid; the PDU/outlet indices identify each plug.
    """
    return SNMPTree(
        base=".1.3.6.1.4.1.13742.6",
        oids=[
            OIDEnd(),  # PlugMeasurement.index: pduId.outletId
            "3.5.3.1.2",  # outletLabel: label printed on the PDU
            "3.5.3.1.3",  # outletName: user-defined name
            "4.1.2.1.3",  # outletSwitchingState: on(7)/off(8); other states map to unknown
        ],
    )


snmp_section_raritan_pdu_plugs = SimpleSNMPSection(
    name="raritan_pdu_plugs",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.6"),
        any_of(
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX2-2"),
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX3"),
        ),
    ),
    fetch=_plug_tree(),
    parse_function=parse_raritan_pdu_plugs,
)


check_plugin_raritan_pdu_plugs = CheckPlugin(
    name="raritan_pdu_plugs",
    service_name="Plug %s",
    discovery_function=discover_raritan_pdu_plugs,
    check_function=check_raritan_pdu_plugs,
    check_ruleset_name="plugs",
    check_default_parameters={"required_state": None},
)

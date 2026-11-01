#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import Field

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.raritan.lib import ParsedModel, scale_sensor_value, STATE_MAPPING


class ProtectorMeasurement(ParsedModel):
    """One measurement row, in SNMP fetch order; values depend on sensor type."""

    index: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    state: str
    value: str  # Empty/unused values are valid for state-only sensors.
    availability: str = "1"  # TruthValue: 1 = present, 2 = absent.


class ProtectorPrecision(ParsedModel):
    """One precision row; an empty decimal field means no usable scaling."""

    index: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    decimals: str


class ProtectorData(ParsedModel):
    """Scaled data for one protector, with independently optional readings."""

    state: str | None = None
    current: float | None = None
    current_problem: tuple[State, str] | None = None


type Section = Mapping[str, ProtectorData]


_STATES = {
    "-1": (State.UNKNOWN, "Overcurrent protector information is unavailable"),
    "0": (State.CRIT, "Overcurrent protector is open"),
    "1": (State.OK, "Overcurrent protector is closed"),
}

# Both tables use the suffix PDU.protector.sensor_type. Join exact suffixes;
# the binary trip sensor (15) does not require a decimal precision entry.


def parse_raritan_pdu_ocprot(
    string_table: Sequence[StringTable],
) -> dict[str, ProtectorData]:
    # Retain compatibility with cached three-column rows from the previous fetch.
    measurements = [
        ProtectorMeasurement.model_validate(dict(zip(tuple(ProtectorMeasurement.model_fields)[:len(row)], row, strict=True)))
        for row in string_table[0]
    ]
    precisions = [
        ProtectorPrecision.model_validate(dict(zip(ProtectorPrecision.model_fields, row, strict=True)))
        for row in string_table[1]
    ]
    scales = {precision.index: precision.decimals for precision in precisions}
    multiple_pdus = len({row.index.split(".")[0] for row in (*measurements, *precisions)}) > 1
    parsed: dict[str, ProtectorData] = {}
    for measurement in measurements:
        pdu, protector, sensor_type = measurement.index.split(".")
        protector_id = f"{pdu}/C{protector}" if multiple_pdus else f"C{protector}"
        previous = parsed.get(protector_id)

        if sensor_type == "15":
            parsed[protector_id] = ProtectorData(
                state=measurement.state if measurement.availability == "1" else "-1",
                current=previous.current if previous is not None else None,
                current_problem=previous.current_problem if previous is not None else None,
            )
        elif sensor_type == "1":
            current = None
            problem = None
            if measurement.availability != "1" or measurement.state == "-1":
                problem = (State.UNKNOWN, "Current sensor is unavailable")
            else:
                state, text = STATE_MAPPING.get(measurement.state, (State.UNKNOWN, "unhandled state"))
                if state is not State.OK:
                    problem = (state, f"Current sensor state: {text}")
                scale = scales.get(measurement.index)
                if scale not in (None, "") and measurement.value != "":
                    try:
                        current = scale_sensor_value(measurement.value, scale)
                    except (ValueError, OverflowError):
                        problem = (State.UNKNOWN, "Invalid or missing current reading")
            if current is not None or problem is not None:
                parsed[protector_id] = ProtectorData(
                    state=previous.state if previous is not None else None,
                    current=current,
                    current_problem=problem,
                )
    return parsed


def discover_raritan_pdu_ocprot(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_raritan_pdu_ocprot(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    if data.state is not None:
        state, state_readable = _STATES.get(
            data.state,
            (State.UNKNOWN, f"Unknown overcurrent protector state: {data.state or 'missing'}"),
        )
        yield Result(state=state, summary=state_readable)

    if data.current_problem is not None:
        state, text = data.current_problem
        yield Result(state=state, summary=text)

    if data.current is not None:
        yield from check_levels_v1(
            data.current,
            metric_name="current",
            levels_upper=params["levels"],
            render_func=lambda x: f"{x:.2f} A",
            label="Current",
        )


def _ocprot_trees() -> list[SNMPTree]:
    """Fetch PDU2-MIB overcurrent protector measurements and decimal precision.

    Measurement entry: .1.3.6.1.4.1.13742.6.5.3.3.1
    Configuration entry: .1.3.6.1.4.1.13742.6.3.4.4.1
    Both use the OID suffix .<pduId>.<overCurrentProtectorIndex>.<sensorType>.
    Sensor type 1 provides RMS current; type 15 provides the trip state.

    Checkmk aligns each tree's columns by OID suffix. zip() then maps each
    individual row to the corresponding Pydantic model in fetch order. The
    two tables are joined by the complete index, independently of row order.
    Trip states do not require a matching precision row.
    """
    return [
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.5.3.3.1",
            oids=[
                OIDEnd(),  # ProtectorMeasurement.index: PDU.protector.sensorType
                "3",  # measurementsOverCurrentProtectorSensorState
                "4",  # measurementsOverCurrentProtectorSensorValue (unsigned)
                "2",  # measurementsOverCurrentProtectorSensorIsAvailable (TruthValue)
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.4.4.1",
            oids=[
                OIDEnd(),  # ProtectorPrecision.index: same full sensor identity
                "7",  # overCurrentProtectorSensorDecimalDigits: divide by 10**digits
            ],
        ),
    ]


snmp_section_raritan_pdu_ocprot = SNMPSection(
    name="raritan_pdu_ocprot",
    detect=contains(".1.3.6.1.2.1.1.2.0", "13742"),
    fetch=_ocprot_trees(),
    parse_function=parse_raritan_pdu_ocprot,
)


check_plugin_raritan_pdu_ocprot = CheckPlugin(
    name="raritan_pdu_ocprot",
    service_name="Overcurrent Protector %s",
    discovery_function=discover_raritan_pdu_ocprot,
    check_function=check_raritan_pdu_ocprot,
    check_ruleset_name="ocprot_current",
    check_default_parameters={"levels": (14.0, 15.0)},
)

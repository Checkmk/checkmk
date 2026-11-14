#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.raritan.lib import DETECT_RARITAN, ParsedModel


class HardwareFailure(BaseModel):
    """One hwFailureEntry; SNMP numeric strings are validated as integers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+\.\d+$")
    component_id: str
    failure_type: int
    asserted: int = Field(ge=1, le=2)  # SNMP TruthValue: true(1), false(2)
    last_assert_timestamp: int = Field(ge=0, le=4294967295)
    last_deassert_timestamp: int = Field(ge=0, le=4294967295)
    assert_count: int = Field(ge=0, le=4294967295)

    @property
    def active(self) -> bool:
        return self.last_deassert_timestamp == 0


class HardwareFailureSection(ParsedModel):
    # Keep a parsed section even for an empty table, so discovery and checking
    # can report the healthy state before any hardware failure has occurred.
    failures: tuple[HardwareFailure, ...]


_FAILURE_TYPES = {
    1: "Network device not detected",
    2: "I2C bus stuck",
    3: "Subcontroller not reachable",
    4: "Subcontroller malfunction",
    5: "Outlet power state inconsistent",
}


def parse_raritan_pdu_hw_failure(
        string_table: StringTable
) -> HardwareFailureSection:
    """Map each aligned SNMP row to model fields in the fetch column order."""
    return HardwareFailureSection(failures=tuple(
        HardwareFailure.model_validate(dict(zip(HardwareFailure.model_fields, row, strict=True)))
        for row in string_table
    ))


def discover_raritan_pdu_hw_failure(
        section: HardwareFailureSection
) -> DiscoveryResult:
    yield Service()


def _timestamp(
        value: int
) -> str:
    return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if value else "not reported"


def check_raritan_pdu_hw_failure(
        section: HardwareFailureSection
) -> CheckResult:
    if not section.failures:
        yield Result(state=State.OK, summary="No hardware failures reported")
        return

    active_count = sum(failure.active for failure in section.failures)
    cleared_count = len(section.failures) - active_count
    yield Result(
        state=State.OK,
        summary=f"Active hardware failures: {active_count}, cleared entries: {cleared_count}",
    )
    multiple_pdus = len({failure.index.split(".")[0] for failure in section.failures}) > 1
    for failure in section.failures:
        pdu, entry = failure.index.split(".")
        component = failure.component_id or "Unspecified component"
        failure_type = _FAILURE_TYPES.get(failure.failure_type, f"Unknown failure type ({failure.failure_type})")
        prefix = f"PDU {pdu}: " if multiple_pdus else ""
        text = f"{prefix}{component}: {failure_type}"
        details = (
            f"PDU {pdu}, entry {entry}: {component}: {failure_type}\n"
            f"Status: {'active' if failure.active else 'cleared'}, "
            f"device asserted: {'yes' if failure.asserted == 1 else 'no'}\n"
            f"Last asserted: {_timestamp(failure.last_assert_timestamp)}\n"
            f"Last deasserted: {'not cleared (0)' if failure.active else _timestamp(failure.last_deassert_timestamp)}\n"
            f"Assertion count: {failure.assert_count}"
        )
        if failure.active:
            yield Result(state=State.CRIT, summary=text, details=details)
        else:
            yield Result(state=State.OK, notice=f"Cleared: {text}", details=details)


def _hw_failure_tree() -> SNMPTree:
    """Fetch PDU2-MIB::hwFailureTable, indexed by pduId and hwFailureIndex.

    Table: .1.3.6.1.4.1.13742.6.10.3.1
    Entry: .1.3.6.1.4.1.13742.6.10.3.1.1
    Each column's OID ends in .<pduId>.<hwFailureIndex>.
    Column 1 is a non-readable index; OIDEnd() supplies both index components.

    The fetch order matches HardwareFailure.model_fields. Checkmk aligns the
    columns by OID suffix before zip() assigns each row to the model fields.
    Epoch timestamps are seconds since 1970-01-01 00:00:00 UTC.
    """
    return SNMPTree(
        base=".1.3.6.1.4.1.13742.6.10.3.1.1",
        oids=[
            OIDEnd(),  # index: pduId.hwFailureIndex
            "2",  # hwFailureComponentId: affected hardware component
            "3",  # hwFailureType: HwFailureTypeEnumeration
            "4",  # hwFailureAsserted: SNMP TruthValue, true(1)/false(2)
            "5",  # hwFailureLastAssertTimeStamp: last assertion, Unix seconds
            "6",  # hwFailureLastDeassertTimeStamp: last clearing, 0 while active
            "7",  # hwFailureAssertCount: number of assertions
        ],
    )


snmp_section_raritan_pdu_hw_failure = SimpleSNMPSection(
    name="raritan_pdu_hw_failure",
    detect=DETECT_RARITAN,
    fetch=_hw_failure_tree(),
    parse_function=parse_raritan_pdu_hw_failure,
)

check_plugin_raritan_pdu_hw_failure = CheckPlugin(
    name="raritan_pdu_hw_failure",
    service_name="HW-Failure",
    discovery_function=discover_raritan_pdu_hw_failure,
    check_function=check_raritan_pdu_hw_failure,
)

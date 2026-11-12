# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Raritan inlet summaries, from native PDU2-MIB configuration data."""

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import (
    InventoryPlugin, InventoryResult, OIDEnd, SimpleSNMPSection, SNMPTree, TableRow,
    StringByteTable, OIDBytes,
)
from cmk.plugins.raritan.lib import DETECT_RARITAN
from cmk.plugins.raritan.inventory import InventoryCapabilities, InventoryInteger, InventoryTruthValue


class InletConfiguration(BaseModel):
    """One aligned SNMP row in fetch order; missing optional numbers stay unknown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+\.\d+$")
    label: str
    name: str
    pole_count: InventoryInteger
    rated_voltage: str
    rated_current: str
    plug: str
    sensor_capabilities: InventoryCapabilities
    is_dc: InventoryTruthValue
    line_pair_count: InventoryInteger


def parse_raritan_pdu_inventory_inlet_summary(
        string_table: StringByteTable
) -> tuple[InletConfiguration, ...]:
    return tuple(
        InletConfiguration.model_validate(dict(zip(InletConfiguration.model_fields, row, strict=True)))
        for row in string_table
    )


def inventory_raritan_pdu_inventory_inlet_summary(
        section: tuple[InletConfiguration, ...]
) -> InventoryResult:
    for row in section:
        columns = row.model_dump(exclude={"index"}, exclude_none=True)
        yield TableRow(
            path=["hardware", "components", "raritan_pdu_inlets"],
            key_columns=dict(zip(('pdu_id', 'inlet_id'), map(int, row.index.split(".")), strict=True)),
            inventory_columns={key: value for key, value in columns.items() if value != ""},
        )


snmp_section_raritan_pdu_inventory_inlet_summary = SimpleSNMPSection(
    name="raritan_pdu_inventory_inlet_summary",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6.3.3.3.1",
        oids=[
            OIDEnd(),  # pdu_id.inlet_id
            "2",  # inletLabel
            "3",  # inletName
            "5",  # inletPoleCount
            "6",  # inletRatedVoltage
            "7",  # inletRatedCurrent
            "12",  # inletPlugDescriptor
            OIDBytes("10"),  # inletDeviceCapabilities
            "15",  # inletIsDC
            "16",  # inletLinePairCount
        ],
    ),
    parse_function=parse_raritan_pdu_inventory_inlet_summary,
)

inventory_plugin_raritan_pdu_inventory_inlet_summary = InventoryPlugin(
    name="raritan_pdu_inventory_inlet_summary",
    sections=["raritan_pdu_inventory_inlet_summary"],
    inventory_function=inventory_raritan_pdu_inventory_inlet_summary,
)

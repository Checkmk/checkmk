# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Raritan outlet summaries, from native PDU2-MIB configuration data."""

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import (
    InventoryPlugin, InventoryResult, OIDEnd, SimpleSNMPSection, SNMPTree, TableRow,
    StringByteTable, OIDBytes,
)
from cmk.plugins.raritan.lib import DETECT_RARITAN
from cmk.plugins.raritan.inventory import InventoryCapabilities, InventoryInteger, InventoryTruthValue
from cmk.plugins.raritan.inventory import PowerSourceConfiguration, power_source_names, resolve_power_source


class OutletConfiguration(BaseModel):
    """One aligned SNMP row in fetch order; missing optional numbers stay unknown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+\.\d+$")
    label: str
    name: str
    pole_count: InventoryInteger
    rated_voltage: str
    rated_current: str
    rated_va: str
    receptacle: str
    switchable: InventoryTruthValue
    sensor_capabilities: InventoryCapabilities
    power_source: str


def parse_raritan_pdu_inventory_outlet_summary(
        string_table: StringByteTable
) -> tuple[OutletConfiguration, ...]:
    return tuple(
        OutletConfiguration.model_validate(dict(zip(OutletConfiguration.model_fields, row, strict=True)))
        for row in string_table
    )


def inventory_raritan_pdu_inventory_outlet_summary(
    section_raritan_pdu_inventory_outlet_summary: tuple[OutletConfiguration, ...] | None,
    section_raritan_pdu_inventory_inlet_summary: tuple[PowerSourceConfiguration, ...] | None,
    section_raritan_pdu_inventory_ocprot: tuple[PowerSourceConfiguration, ...] | None,
    section_raritan_pdu_inventory_transfer_switch: tuple[PowerSourceConfiguration, ...] | None,
) -> InventoryResult:
    names = power_source_names(
        section_raritan_pdu_inventory_inlet_summary,
        section_raritan_pdu_inventory_ocprot,
        section_raritan_pdu_inventory_transfer_switch,
    )
    for row in section_raritan_pdu_inventory_outlet_summary or ():
        columns = row.model_dump(exclude={"index"}, exclude_none=True)
        columns["power_source"] = resolve_power_source(row.power_source, names, int(row.index.split(".")[0]))
        yield TableRow(
            path=["hardware", "components", "raritan_pdu_outlets"],
            key_columns=dict(zip(('pdu_id', 'outlet_id'), map(int, row.index.split(".")), strict=True)),
            inventory_columns={key: value for key, value in columns.items() if value != ""},
        )


snmp_section_raritan_pdu_inventory_outlet_summary = SimpleSNMPSection(
    name="raritan_pdu_inventory_outlet_summary",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6.3.5.3.1",
        oids=[
            OIDEnd(),  # pdu_id.outlet_id
            "2",  # outletLabel
            "3",  # outletName
            "5",  # outletPoleCount
            "6",  # outletRatedVoltage
            "7",  # outletRatedCurrent
            "8",  # outletRatedVA
            "29",  # outletReceptacleDescriptor
            "28",  # outletSwitchable
            OIDBytes("10"),  # outletDeviceCapabilities
            "33",  # outletPowerSource
        ],
    ),
    parse_function=parse_raritan_pdu_inventory_outlet_summary,
)

inventory_plugin_raritan_pdu_inventory_outlet_summary = InventoryPlugin(
    name="raritan_pdu_inventory_outlet_summary",
    sections=[
        "raritan_pdu_inventory_outlet_summary",
        "raritan_pdu_inventory_inlet_summary",
        "raritan_pdu_inventory_ocprot",
        "raritan_pdu_inventory_transfer_switch",
    ],
    inventory_function=inventory_raritan_pdu_inventory_outlet_summary,
)

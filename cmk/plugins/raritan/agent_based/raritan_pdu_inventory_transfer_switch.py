# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Transfer switch hardware and wiring from PDU2-MIB configuration."""

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import (
    InventoryPlugin, InventoryResult, OIDBytes, OIDEnd, SimpleSNMPSection,
    SNMPTree, StringByteTable, TableRow,
)
from cmk.plugins.raritan.inventory import InventoryCapabilities, InventoryInteger
from cmk.plugins.raritan.inventory import PowerSourceConfiguration, power_source_names, resolve_power_source
from cmk.plugins.raritan.lib import DETECT_RARITAN


class TransferSwitchConfiguration(BaseModel):
    """One configuration row in SNMP fetch order, indexed by PDU and switch."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+\.\d+$")
    label: str
    name: str
    preferred_inlet: InventoryInteger
    pole_count: InventoryInteger
    sensor_capabilities: InventoryCapabilities
    power_source_1: str
    power_source_2: str


def parse_raritan_pdu_inventory_transfer_switch(
    string_table: StringByteTable,
) -> tuple[TransferSwitchConfiguration, ...]:
    return tuple(
        TransferSwitchConfiguration.model_validate(
            dict(zip(TransferSwitchConfiguration.model_fields, row, strict=True))
        )
        for row in string_table
    )


def inventory_raritan_pdu_inventory_transfer_switch(
    section_raritan_pdu_inventory_transfer_switch: tuple[TransferSwitchConfiguration, ...] | None,
    section_raritan_pdu_inventory_inlet_summary: tuple[PowerSourceConfiguration, ...] | None,
    section_raritan_pdu_inventory_ocprot: tuple[PowerSourceConfiguration, ...] | None,
) -> InventoryResult:
    names = power_source_names(
        section_raritan_pdu_inventory_inlet_summary,
        section_raritan_pdu_inventory_ocprot,
        section_raritan_pdu_inventory_transfer_switch,
    )
    for row in section_raritan_pdu_inventory_transfer_switch or ():
        columns = row.model_dump(exclude={"index"}, exclude_none=True)
        columns["power_source_1"] = resolve_power_source(row.power_source_1, names, int(row.index.split(".")[0]))
        columns["power_source_2"] = resolve_power_source(row.power_source_2, names, int(row.index.split(".")[0]))
        yield TableRow(
            path=["hardware", "components", "raritan_pdu_transfer_switches"],
            key_columns=dict(zip(("pdu_id", "transfer_switch_id"), map(int, row.index.split(".")), strict=True)),
            inventory_columns={key: value for key, value in columns.items() if value != ""},
        )


snmp_section_raritan_pdu_inventory_transfer_switch = SimpleSNMPSection(
    name="raritan_pdu_inventory_transfer_switch",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6.3.9.3.1",  # transferSwitchConfigurationEntry
        oids=[
            OIDEnd(),  # pduId.transferSwitchId
            "2",  # transferSwitchLabel
            "3",  # transferSwitchName
            "4",  # transferSwitchPreferredInlet (configured preference, not active inlet)
            "5",  # transferSwitchPoleCount
            OIDBytes("24"),  # transferSwitchCapabilities (sensor BITS)
            "31",  # transferSwitchPowerSource1 (RowPointer, typically protectorLabel)
            "32",  # transferSwitchPowerSource2 (RowPointer, typically protectorLabel)
        ],
    ),
    parse_function=parse_raritan_pdu_inventory_transfer_switch,
)

inventory_plugin_raritan_pdu_inventory_transfer_switch = InventoryPlugin(
    name="raritan_pdu_inventory_transfer_switch",
    sections=[
        "raritan_pdu_inventory_transfer_switch",
        "raritan_pdu_inventory_inlet_summary",
        "raritan_pdu_inventory_ocprot",
    ],
    inventory_function=inventory_raritan_pdu_inventory_transfer_switch,
)

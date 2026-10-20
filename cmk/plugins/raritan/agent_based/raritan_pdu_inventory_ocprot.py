# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Overcurrent protector hardware from the PDU2-MIB configuration table."""

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import (
    InventoryPlugin, InventoryResult, OIDBytes, OIDEnd, SimpleSNMPSection,
    SNMPTree, StringByteTable, TableRow,
)
from cmk.plugins.raritan.inventory import InventoryCapabilities, InventoryInteger
from cmk.plugins.raritan.inventory import PowerSourceConfiguration, power_source_names, resolve_power_source
from cmk.plugins.raritan.lib import DETECT_RARITAN


class OvercurrentProtectorConfiguration(BaseModel):
    """One configuration row, in SNMP fetch order, identified by PDU and protector."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+\.\d+$")
    label: str
    name: str
    protector_type: InventoryInteger
    rated_current: str
    pole_count: InventoryInteger
    sensor_capabilities: InventoryCapabilities
    power_source: str


def parse_raritan_pdu_inventory_ocprot(
    string_table: StringByteTable,
) -> tuple[OvercurrentProtectorConfiguration, ...]:
    return tuple(
        OvercurrentProtectorConfiguration.model_validate(
            dict(zip(OvercurrentProtectorConfiguration.model_fields, row, strict=True))
        )
        for row in string_table
    )


def inventory_raritan_pdu_inventory_ocprot(
    section_raritan_pdu_inventory_ocprot: tuple[OvercurrentProtectorConfiguration, ...] | None,
    section_raritan_pdu_inventory_inlet_summary: tuple[PowerSourceConfiguration, ...] | None,
    section_raritan_pdu_inventory_transfer_switch: tuple[PowerSourceConfiguration, ...] | None,
) -> InventoryResult:
    names = power_source_names(
        section_raritan_pdu_inventory_inlet_summary,
        section_raritan_pdu_inventory_ocprot,
        section_raritan_pdu_inventory_transfer_switch,
    )
    for row in section_raritan_pdu_inventory_ocprot or ():
        columns = row.model_dump(exclude={"index"}, exclude_none=True)
        columns["power_source"] = resolve_power_source(row.power_source, names, int(row.index.split(".")[0]))
        yield TableRow(
            path=["hardware", "components", "raritan_pdu_overcurrent_protectors"],
            key_columns=dict(zip(("pdu_id", "protector_id"), map(int, row.index.split(".")), strict=True)),
            inventory_columns={key: value for key, value in columns.items() if value != ""},
        )


snmp_section_raritan_pdu_inventory_ocprot = SimpleSNMPSection(
    name="raritan_pdu_inventory_ocprot",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6.3.4.3.1",  # overCurrentProtectorConfigurationEntry
        oids=[
            OIDEnd(),  # pduId.overCurrentProtectorIndex
            "2",  # overCurrentProtectorLabel
            "3",  # overCurrentProtectorName
            "4",  # overCurrentProtectorType
            "5",  # overCurrentProtectorRatedCurrent (device text, e.g. 16A)
            "6",  # overCurrentProtectorPoleCount
            OIDBytes("9"),  # overCurrentProtectorCapabilities (sensor BITS)
            "10",  # overCurrentProtectorPowerSource (RowPointer OID)
        ],
    ),
    parse_function=parse_raritan_pdu_inventory_ocprot,
)

inventory_plugin_raritan_pdu_inventory_ocprot = InventoryPlugin(
    name="raritan_pdu_inventory_ocprot",
    sections=[
        "raritan_pdu_inventory_ocprot",
        "raritan_pdu_inventory_inlet_summary",
        "raritan_pdu_inventory_transfer_switch",
    ],
    inventory_function=inventory_raritan_pdu_inventory_ocprot,
)

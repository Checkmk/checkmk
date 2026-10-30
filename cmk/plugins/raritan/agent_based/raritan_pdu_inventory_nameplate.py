# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Raritan PDU nameplates, from native PDU2-MIB configuration data."""

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import (
    InventoryPlugin, InventoryResult, OIDEnd, SimpleSNMPSection, SNMPTree, TableRow,
    StringTable,
)
from cmk.plugins.raritan.lib import DETECT_RARITAN


class Nameplate(BaseModel):
    """One aligned SNMP row in fetch order; missing optional numbers stay unknown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+$")
    manufacturer: str
    model: str
    serial_number: str
    rated_voltage: str
    rated_current: str
    rated_frequency: str
    rated_va: str
    wiring_diagram_url: str


def parse_raritan_pdu_inventory_nameplate(
        string_table: StringTable
) -> tuple[Nameplate, ...]:
    return tuple(
        Nameplate.model_validate(dict(zip(Nameplate.model_fields, row, strict=True)))
        for row in string_table
    )


def inventory_raritan_pdu_inventory_nameplate(
        section: tuple[Nameplate, ...]
) -> InventoryResult:
    for row in section:
        columns = row.model_dump(exclude={"index"}, exclude_none=True)
        yield TableRow(
            path=["hardware", "components", "raritan_pdu_nameplates"],
            key_columns=dict(zip(('pdu_id',), map(int, row.index.split(".")), strict=True)),
            inventory_columns={key: value for key, value in columns.items() if value != ""},
        )


snmp_section_raritan_pdu_inventory_nameplate = SimpleSNMPSection(
    name="raritan_pdu_inventory_nameplate",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6.3.2.1.1",
        oids=[
            OIDEnd(),  # pdu_id
            "2",  # pduManufacturer
            "3",  # pduModel
            "4",  # pduSerialNumber
            "5",  # pduRatedVoltage
            "6",  # pduRatedCurrent
            "7",  # pduRatedFrequency
            "8",  # pduRatedVA
            "9",  # pduImage
        ],
    ),
    parse_function=parse_raritan_pdu_inventory_nameplate,
)

inventory_plugin_raritan_pdu_inventory_nameplate = InventoryPlugin(
    name="raritan_pdu_inventory_nameplate",
    sections=["raritan_pdu_inventory_nameplate"],
    inventory_function=inventory_raritan_pdu_inventory_nameplate,
)

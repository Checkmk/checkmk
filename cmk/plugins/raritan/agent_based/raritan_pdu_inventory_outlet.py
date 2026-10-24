# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Raritan outlet poles, including configured conductors without live measurements."""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import (
    InventoryPlugin, InventoryResult, OIDBytes, OIDEnd, SNMPSection, SNMPTree,
    StringByteTable, TableRow,
)
from cmk.plugins.raritan.lib import DETECT_RARITAN
from cmk.plugins.raritan.inventory import InventoryCapabilities, InventoryInteger


class OutletPole(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    line: InventoryInteger
    node: InventoryInteger


class OutletIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+\.\d+$")
    label: str
    name: str
    sensor_capabilities: InventoryCapabilities


class OutletPoleSection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    poles: tuple[OutletPole, ...]
    connectors: tuple[OutletIdentity, ...]


def parse_raritan_pdu_inventory_outlet(
        string_table: Sequence[StringByteTable]
) -> OutletPoleSection:
    return OutletPoleSection(
        poles=tuple(OutletPole.model_validate(dict(zip(OutletPole.model_fields, row, strict=True)))
                    for row in string_table[0]),
        connectors=tuple(OutletIdentity.model_validate(dict(zip(OutletIdentity.model_fields, row, strict=True)))
                         for row in string_table[1]),
    )


def inventory_raritan_pdu_inventory_outlet(
        section: OutletPoleSection
) -> InventoryResult:
    parents = {row.index: row for row in section.connectors}
    for pole in section.poles:
        columns = pole.model_dump(exclude={"index"}, exclude_none=True)
        if (parent := parents.get(pole.index.rsplit(".", 1)[0])) is not None:
            columns.update(parent.model_dump(exclude={"index"}))
        yield TableRow(
            path=["hardware", "components", "raritan_pdu_outlet_poles"],
            key_columns=dict(zip(('pdu_id', 'outlet_id', 'pole_index'), map(int, pole.index.split(".")), strict=True)),
            inventory_columns={key: value for key, value in columns.items() if value != ""},
        )


snmp_section_raritan_pdu_inventory_outlet = SNMPSection(
    name="raritan_pdu_inventory_outlet",
    detect=DETECT_RARITAN,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.5.5.1",  # outletPoleConfigurationEntry
            oids=[
                OIDEnd(),  # PDU.outlet.pole
                "1",  # outletPoleLine: 1=L1, 2=L2, 3=L3, 4=N, 5=DC+, 6=DC-
                "2",  # outletPoleNode: physical topology node
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.5.3.1",  # outletConfigurationEntry
            oids=[
                OIDEnd(),  # PDU.outlet; join by index, never by row position
                "2",  # outletLabel
                "3",  # outletName
                OIDBytes("11"),  # outletPoleCapabilities
            ],
        ),
    ],
    parse_function=parse_raritan_pdu_inventory_outlet,
)

inventory_plugin_raritan_pdu_inventory_outlet = InventoryPlugin(
    name="raritan_pdu_inventory_outlet",
    sections=["raritan_pdu_inventory_outlet"],
    inventory_function=inventory_raritan_pdu_inventory_outlet,
)

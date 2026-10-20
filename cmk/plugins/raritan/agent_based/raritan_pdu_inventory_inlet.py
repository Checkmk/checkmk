# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Raritan inlet poles, including configured conductors without live measurements."""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import (
    InventoryPlugin, InventoryResult, OIDBytes, OIDEnd, SNMPSection, SNMPTree,
    StringByteTable, TableRow,
)
from cmk.plugins.raritan.lib import DETECT_RARITAN
from cmk.plugins.raritan.inventory import InventoryCapabilities, InventoryInteger


class InletPole(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    line: InventoryInteger
    node: InventoryInteger


class InletIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+\.\d+$")
    label: str
    name: str
    sensor_capabilities: InventoryCapabilities


class InletPoleSection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    poles: tuple[InletPole, ...]
    connectors: tuple[InletIdentity, ...]


def parse_raritan_pdu_inventory_inlet(
        string_table: Sequence[StringByteTable]
) -> InletPoleSection:
    return InletPoleSection(
        poles=tuple(InletPole.model_validate(dict(zip(InletPole.model_fields, row, strict=True)))
                    for row in string_table[0]),
        connectors=tuple(InletIdentity.model_validate(dict(zip(InletIdentity.model_fields, row, strict=True)))
                         for row in string_table[1]),
    )


def inventory_raritan_pdu_inventory_inlet(
        section: InletPoleSection
) -> InventoryResult:
    parents = {row.index: row for row in section.connectors}
    for pole in section.poles:
        columns = pole.model_dump(exclude={"index"}, exclude_none=True)
        if (parent := parents.get(pole.index.rsplit(".", 1)[0])) is not None:
            columns.update(parent.model_dump(exclude={"index"}))
        yield TableRow(
            path=["hardware", "components", "raritan_pdu_inlet_poles"],
            key_columns=dict(zip(('pdu_id', 'inlet_id', 'pole_index'), map(int, pole.index.split(".")), strict=True)),
            inventory_columns={key: value for key, value in columns.items() if value != ""},
        )


snmp_section_raritan_pdu_inventory_inlet = SNMPSection(
    name="raritan_pdu_inventory_inlet",
    detect=DETECT_RARITAN,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.3.5.1",  # inletPoleConfigurationEntry
            oids=[
                OIDEnd(),  # PDU.inlet.pole
                "1",  # inletPoleLine: 1=L1, 2=L2, 3=L3, 4=N, 5=DC+, 6=DC-
                "2",  # inletPoleNode: physical topology node
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.3.3.1",  # inletConfigurationEntry
            oids=[
                OIDEnd(),  # PDU.inlet; join by index, never by row position
                "2",  # inletLabel
                "3",  # inletName
                OIDBytes("11"),  # inletPoleCapabilities
            ],
        ),
    ],
    parse_function=parse_raritan_pdu_inventory_inlet,
)

inventory_plugin_raritan_pdu_inventory_inlet = InventoryPlugin(
    name="raritan_pdu_inventory_inlet",
    sections=["raritan_pdu_inventory_inlet"],
    inventory_function=inventory_raritan_pdu_inventory_inlet,
)

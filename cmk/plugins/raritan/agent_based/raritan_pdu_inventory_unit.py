# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Raritan PDU hardware, from native PDU2-MIB configuration data."""

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import (
    InventoryPlugin, InventoryResult, OIDEnd, SimpleSNMPSection, SNMPTree, TableRow,
    StringByteTable, OIDBytes,
)
from cmk.plugins.raritan.lib import DETECT_RARITAN
from cmk.plugins.raritan.inventory import InventoryCapabilities, InventoryInteger, InventoryTruthValue


class UnitConfiguration(BaseModel):
    """One aligned SNMP row in fetch order; missing optional numbers stay unknown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+$")
    name: str
    inlet_count: InventoryInteger
    overcurrent_protector_count: InventoryInteger
    outlet_count: InventoryInteger
    inlet_controller_count: InventoryInteger
    outlet_controller_count: InventoryInteger
    external_sensor_capacity: InventoryInteger
    managed_external_sensor_count: InventoryInteger
    transfer_switch_count: InventoryInteger
    metering_controller_count: InventoryInteger
    circuit_count: InventoryInteger
    peripheral_device_package_count: InventoryInteger
    product_type: InventoryInteger
    sensor_capabilities: InventoryCapabilities
    has_dc_inlets: InventoryTruthValue
    cascade_role: InventoryInteger
    cascade_type: InventoryInteger
    cascade_position: InventoryInteger
    orientation: InventoryInteger


def parse_raritan_pdu_inventory_unit(
        string_table: StringByteTable
) -> tuple[UnitConfiguration, ...]:
    return tuple(
        UnitConfiguration.model_validate(dict(zip(UnitConfiguration.model_fields, row, strict=True)))
        for row in string_table
    )


def inventory_raritan_pdu_inventory_unit(
        section: tuple[UnitConfiguration, ...]
) -> InventoryResult:
    for row in section:
        columns = row.model_dump(exclude={"index"}, exclude_none=True)
        yield TableRow(
            path=["hardware", "components", "raritan_pdu_units"],
            key_columns=dict(zip(('pdu_id',), map(int, row.index.split(".")), strict=True)),
            inventory_columns={key: value for key, value in columns.items() if value != ""},
        )


snmp_section_raritan_pdu_inventory_unit = SimpleSNMPSection(
    name="raritan_pdu_inventory_unit",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6.3.2.2.1",
        oids=[
            OIDEnd(),  # pdu_id
            "13",  # pduName
            "2",  # inletCount
            "3",  # overCurrentProtectorCount
            "4",  # outletCount
            "5",  # inletControllerCount
            "6",  # outletControllerCount
            "7",  # externalSensorCount
            "42",  # managedExternalSensorCount
            "66",  # transferSwitchCount
            "68",  # meteringControllerCount
            "76",  # circuitCount
            "79",  # peripheralDevicePackageCount
            "67",  # productType
            OIDBytes("35"),  # unitDeviceCapabilities
            "83",  # hasDCInlets
            "41",  # pduDaisychainMemberType
            "70",  # deviceCascadeType
            "71",  # deviceCascadePosition
            "84",  # pduOrientation
        ],
    ),
    parse_function=parse_raritan_pdu_inventory_unit,
)

inventory_plugin_raritan_pdu_inventory_unit = InventoryPlugin(
    name="raritan_pdu_inventory_unit",
    sections=["raritan_pdu_inventory_unit"],
    inventory_function=inventory_raritan_pdu_inventory_unit,
)

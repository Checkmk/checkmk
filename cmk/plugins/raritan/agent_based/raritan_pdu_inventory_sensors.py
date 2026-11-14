# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Raritan external sensors, from native PDU2-MIB configuration data."""

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import (
    InventoryPlugin, InventoryResult, OIDEnd, SimpleSNMPSection, SNMPTree, TableRow,
    StringTable,
)
from cmk.plugins.raritan.lib import DETECT_RARITAN
from cmk.plugins.raritan.inventory import InventoryInteger, InventoryTruthValue


class ExternalSensor(BaseModel):
    """One aligned SNMP row in fetch order; missing optional numbers stay unknown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: str = Field(pattern=r"^\d+\.\d+$")
    sensor_type: InventoryInteger
    serial_number: str
    name: str
    description: str
    x_coordinate: str
    y_coordinate: str
    z_coordinate: str
    channel: InventoryInteger
    binary_subtype: InventoryInteger
    unit: InventoryInteger
    decimal_digits: InventoryInteger
    is_actuator: InventoryTruthValue
    position: str
    available: InventoryTruthValue


def parse_raritan_pdu_inventory_sensors(
        string_table: StringTable
) -> tuple[ExternalSensor, ...]:
    return tuple(
        ExternalSensor.model_validate(dict(zip(ExternalSensor.model_fields, row, strict=True)))
        for row in string_table
    )


def inventory_raritan_pdu_inventory_sensors(
        section: tuple[ExternalSensor, ...]
) -> InventoryResult:
    for row in section:
        # Configuration can retain disconnected or unused slots. Include only
        # confirmed present sensors; no measurement values enter the inventory.
        if row.available is not True or row.sensor_type in (None, 31):
            continue
        columns = row.model_dump(exclude={"index", "available"}, exclude_none=True)
        if row.channel == -1:
            columns.pop("channel", None)
        if row.sensor_type != 14:
            columns.pop("binary_subtype", None)
        if row.unit in (None, -1):
            columns.pop("unit", None)
            columns.pop("decimal_digits", None)
        yield TableRow(
            path=["hardware", "components", "raritan_pdu_external_sensors"],
            key_columns=dict(zip(('pdu_id', 'sensor_id'), map(int, row.index.split(".")), strict=True)),
            inventory_columns={key: value for key, value in columns.items() if value != ""},
        )


snmp_section_raritan_pdu_inventory_sensors = SimpleSNMPSection(
    name="raritan_pdu_inventory_sensors",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6",
        oids=[
            OIDEnd(),  # pdu_id.sensor_id
            "3.6.3.1.2",  # externalSensorType
            "3.6.3.1.3",  # externalSensorSerialNumber
            "3.6.3.1.4",  # externalSensorName
            "3.6.3.1.5",  # externalSensorDescription
            "3.6.3.1.6",  # externalSensorXCoordinate
            "3.6.3.1.7",  # externalSensorYCoordinate
            "3.6.3.1.8",  # externalSensorZCoordinate
            "3.6.3.1.9",  # externalSensorChannelNumber
            "3.6.3.1.10",  # externalOnOffSensorSubtype
            "3.6.3.1.16",  # externalSensorUnits
            "3.6.3.1.17",  # externalSensorDecimalDigits
            "3.6.3.1.36",  # externalSensorIsActuator
            "3.6.3.1.37",  # externalSensorPosition
            "5.5.3.1.2",  # externalSensorIsAvailable
        ],
    ),
    parse_function=parse_raritan_pdu_inventory_sensors,
)

inventory_plugin_raritan_pdu_inventory_sensors = InventoryPlugin(
    name="raritan_pdu_inventory_sensors",
    sections=["raritan_pdu_inventory_sensors"],
    inventory_function=inventory_raritan_pdu_inventory_sensors,
)

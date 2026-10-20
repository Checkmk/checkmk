# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
"""Legacy PDU-MIB external sensors for older Raritan PX devices."""

from cmk.agent_based.v2 import (
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
    equals,
    CheckPlugin,
    DiscoveryResult,
)
from cmk.plugins.raritan.lib import (
    ExternalSensorRow,
    parse_raritan_sensors,
    ParsedModel,
    check_raritan_sensors,
    check_raritan_sensors_binary,
    check_raritan_sensors_temp,
    discover_raritan_sensors,
    SensorSection,
)


class PxSensorRow(ParsedModel):
    """Legacy PDU-MIB sensor columns in SNMP fetch order; no availability field."""

    sensor_id: str
    sensor_name: str
    sensor_type: str
    sensor_state: str
    sensor_unit: str
    sensor_exponent: str
    sensor_value_str: str
    sensor_lower_crit_str: str
    sensor_lower_warn_str: str
    sensor_upper_crit_str: str
    sensor_upper_warn_str: str


def parse_raritan_px_sensors(string_table: StringTable) -> SensorSection:
    records = []
    for row in string_table:
        raw = PxSensorRow.model_validate(dict(zip(PxSensorRow.model_fields, row, strict=True)))
        # Preserve the legacy name cleanup and availability derived from device state.
        name = raw.sensor_name.replace("Temperature", "").replace("Humidity", "").replace("On/Off", "").strip()
        records.append(ExternalSensorRow(
            **raw.model_dump(exclude={"sensor_name"}),
            sensor_name=name,
            availability="0" if raw.sensor_state == "-1" else "1",
        ))
    return parse_raritan_sensors(records)


snmp_section_raritan_px_sensors = SimpleSNMPSection(
    name="raritan_px_sensors",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.4"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.4.3.3.1",
        oids=[
            "1",  # sensorID
            "4",  # externalSensorName
            "2",  # externalSensorType
            "40",  # externalSensorState
            "16",  # externalSensorUnits
            "17",  # externalSensorDecimalDigits
            "41",  # externalSensorValue
            "31",  # externalSensorLowerCriticalThreshold
            "32",  # externalSensorLowerWarningThreshold
            "33",  # externalSensorUpperCriticalThreshold
            "34",  # externalSensorUpperWarningThreshold
        ],
    ),
    parse_function=parse_raritan_px_sensors,
)


def discover_raritan_px_sensors(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "temp")


check_plugin_raritan_px_sensors = CheckPlugin(
    name="raritan_px_sensors",
    sections=["raritan_px_sensors"],
    service_name="Temperature %s",
    discovery_function=discover_raritan_px_sensors,
    check_function=check_raritan_sensors_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_raritan_px_sensors_humidity(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "humidity")


check_plugin_raritan_px_sensors_humidity = CheckPlugin(
    name="raritan_px_sensors_humidity",
    service_name="Humidity %s",
    sections=["raritan_px_sensors"],
    discovery_function=discover_raritan_px_sensors_humidity,
    check_function=check_raritan_sensors,
)


def discover_raritan_px_sensors_binary(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "binary")


check_plugin_raritan_px_sensors_binary = CheckPlugin(
    name="raritan_px_sensors_binary",
    service_name="Contact %s",
    sections=["raritan_px_sensors"],
    discovery_function=discover_raritan_px_sensors_binary,
    check_function=check_raritan_sensors_binary,
)

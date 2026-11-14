# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
"""EMD-MIB external sensors for Raritan EMX environmental monitors."""

from cmk.agent_based.v2 import (
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
    equals,
    OIDEnd,
    CheckPlugin,
    DiscoveryResult,
)
from cmk.plugins.raritan.lib import (
    ExternalSensorRow,
    parse_raritan_sensors,
    check_raritan_sensors,
    check_raritan_sensors_binary,
    check_raritan_sensors_temp,
    discover_raritan_sensors,
    SensorSection,
)


class EmxSensorRow(ExternalSensorRow):
    """EMD-MIB external sensor row; this fetch has no threshold activation bits."""


def parse_raritan_emx_sensors(string_table: StringTable) -> SensorSection:
    names = tuple(EmxSensorRow.model_fields)[:12]
    records = [EmxSensorRow.model_validate(dict(zip(names, row, strict=True))) for row in string_table]
    return parse_raritan_sensors(records)


snmp_section_raritan_emx_sensors = SimpleSNMPSection(
    name="raritan_emx_sensors",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.8"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.8",
        oids=[
            "2.1.1.1.1",  # externalSensorIsAvailable
            OIDEnd(),  # sensor index (OID suffix)
            "1.2.1.1.5",  # externalSensorName
            "1.2.1.1.2",  # externalSensorType
            "2.1.1.1.2",  # externalSensorState
            "1.2.1.1.11",  # externalSensorUnits
            "1.2.1.1.12",  # externalSensorDecimalDigits
            "2.1.1.1.3",  # externalSensorValue
            "1.2.1.1.20",  # externalSensorLowerCriticalThreshold
            "1.2.1.1.21",  # externalSensorLowerWarningThreshold
            "1.2.1.1.22",  # externalSensorUpperCriticalThreshold
            "1.2.1.1.23",  # externalSensorUpperWarningThreshold
        ],
    ),
    parse_function=parse_raritan_emx_sensors,
)


def discover_raritan_emx_sensors(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "binary")


check_plugin_raritan_emx_sensors = CheckPlugin(
    name="raritan_emx_sensors",
    sections=["raritan_emx_sensors"],
    service_name="Contact %s",
    discovery_function=discover_raritan_emx_sensors,
    check_function=check_raritan_sensors_binary,
)


def discover_raritan_emx_sensors_temp(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "temp")


check_plugin_raritan_emx_sensors_temp = CheckPlugin(
    name="raritan_emx_sensors_temp",
    service_name="Temperature %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_temp,
    check_function=check_raritan_sensors_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_raritan_emx_sensors_airflow(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "airflow")


check_plugin_raritan_emx_sensors_airflow = CheckPlugin(
    name="raritan_emx_sensors_airflow",
    service_name="Air flow %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_airflow,
    check_function=check_raritan_sensors,
)


def discover_raritan_emx_sensors_humidity(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "humidity")


check_plugin_raritan_emx_sensors_humidity = CheckPlugin(
    name="raritan_emx_sensors_humidity",
    service_name="Humidity %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_humidity,
    check_function=check_raritan_sensors,
)


def discover_raritan_emx_sensors_pressure(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "pressure_pa")


check_plugin_raritan_emx_sensors_pressure = CheckPlugin(
    name="raritan_emx_sensors_pressure",
    service_name="Pressure %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_pressure,
    check_function=check_raritan_sensors,
)

# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
"""PDU2-MIB external sensors for PX2/PX3 and compatible PDUs."""

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    SimpleSNMPSection,
    SNMPTree,
    StringByteTable,
    OIDBytes,
    OIDEnd,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
)
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.raritan.lib import (
    ExternalSensorRow,
    parse_raritan_sensors,
    DETECT_RARITAN,
    check_raritan_sensors,
    check_raritan_sensors_temp,
    discover_raritan_sensors,
    SensorSection,
    sensor_reading_problem,
)


class PduSensorRow(ExternalSensorRow):
    """PDU2-MIB external sensor row, including optional threshold activation bits."""


def parse_raritan_px2_sensors(string_table: StringByteTable) -> SensorSection:
    records = []
    for row in string_table:
        names = tuple(PduSensorRow.model_fields)
        # The real SNMP section supplies BITS; retain support for older rows without it.
        fields = dict(zip(names[:12] if len(row) == 12 else names, row, strict=True))
        if "enabled_thresholds" in fields:
            bits = fields["enabled_thresholds"]
            fields["enabled_thresholds"] = tuple(bits.encode("latin-1") if isinstance(bits, str) else bits)
        records.append(PduSensorRow.model_validate(fields))
    return parse_raritan_sensors(records, pdu_indexed=True)


snmp_section_raritan_px2_sensors = SimpleSNMPSection(
    name="raritan_px2_sensors",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6",
        oids=[
            "5.5.3.1.2",  # externalSensorIsAvailable
            OIDEnd(),  # PDU.sensor index
            "3.6.3.1.5",  # externalSensorName
            "3.6.3.1.2",  # externalSensorType
            "5.5.3.1.3",  # externalSensorState
            "3.6.3.1.16",  # externalSensorUnits
            "3.6.3.1.17",  # externalSensorDecimalDigits
            "5.5.3.1.4",  # externalSensorValue
            "3.6.3.1.31",  # externalSensorLowerCriticalThreshold
            "3.6.3.1.32",  # externalSensorLowerWarningThreshold
            "3.6.3.1.33",  # externalSensorUpperCriticalThreshold
            "3.6.3.1.34",  # externalSensorUpperWarningThreshold
            OIDBytes("3.6.3.1.35"),  # externalSensorEnabledThresholds (BITS)
        ],
    ),
    parse_function=parse_raritan_px2_sensors,
)


def discover_raritan_px2_sensors(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "temp")


check_plugin_raritan_px2_sensors = CheckPlugin(
    name="raritan_px2_sensors",
    sections=["raritan_px2_sensors"],
    service_name="Temperature %s",
    discovery_function=discover_raritan_px2_sensors,
    check_function=check_raritan_sensors_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_raritan_px2_sensors_airflow(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "airflow")


check_plugin_raritan_px2_sensors_airflow = CheckPlugin(
    name="raritan_px2_sensors_airflow",
    service_name="Air flow %s",
    sections=["raritan_px2_sensors"],
    discovery_function=discover_raritan_px2_sensors_airflow,
    check_function=check_raritan_sensors,
)


def discover_raritan_px2_sensors_humidity(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "humidity")


def check_raritan_sensors_humidity(
    item: str,
    params: Mapping[str, tuple[float, float]],
    section: SensorSection,
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    if (problem := sensor_reading_problem(sensor)) is not None:
        yield problem
        return
    humidity_value, crit_lower, warn_lower, crit, warn = sensor.sensor_data
    assert humidity_value is not None

    if "levels" in params:
        warn, crit = params["levels"]
    if "levels_lower" in params:
        warn_lower, crit_lower = params["levels_lower"]

    yield from check_humidity(
        humidity=humidity_value,
        params={
            "levels": (warn, crit),
            "levels_lower": (warn_lower, crit_lower),
        },
    )

    state, state_readable = sensor.state
    yield Result(state=state, summary=f"Device status: {state_readable}")


check_plugin_raritan_px2_sensors_humidity = CheckPlugin(
    name="raritan_px2_sensors_humidity",
    service_name="Humidity %s",
    sections=["raritan_px2_sensors"],
    discovery_function=discover_raritan_px2_sensors_humidity,
    check_function=check_raritan_sensors_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={},
)


def discover_raritan_px2_sensors_pressure(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "pressure_pa")


check_plugin_raritan_px2_sensors_pressure = CheckPlugin(
    name="raritan_px2_sensors_pressure",
    service_name="Pressure %s",
    sections=["raritan_px2_sensors"],
    discovery_function=discover_raritan_px2_sensors_pressure,
    check_function=check_raritan_sensors,
)

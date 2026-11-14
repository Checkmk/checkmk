# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Native outlet per-conductor measurements and their SNMP section."""

from collections.abc import Sequence

from cmk.agent_based.v2 import CheckPlugin, OIDBytes, OIDEnd, SNMPSection, SNMPTree, StringByteTable
from cmk.plugins.raritan.lib import (
    check_pdu_electrical,
    DETECT_RARITAN,
    discover_pdu_electrical,
    parse_electrical_section,
    PduSensor,
    PduSensorConfiguration,
    PduSensorMeasurement,
    SensorIndex,
    PduSection as Section,
)

def parse_raritan_pdu_outlet(
        string_table: Sequence[StringByteTable]
) -> Section:
    """Parse native outlet pole tables using the shared Pydantic models."""
    configuration = [
        PduSensorConfiguration.model_validate(dict(zip(PduSensorConfiguration.model_fields, row, strict=True)))
        for row in string_table[0]
    ]
    measurements = [
        PduSensorMeasurement.model_validate(dict(zip(PduSensorMeasurement.model_fields, row, strict=True)))
        for row in string_table[1]
    ]
    config_by_index = {row.oid_end: row for row in configuration}
    measurements_by_index = {row.oid_end: row for row in measurements}
    # zip maps columns within a row; separate tables are joined by the full index.
    sensors = tuple(
        PduSensor(
            index=SensorIndex.from_oid(oid),
            configuration=config_by_index.get(oid),
            measurement=measurements_by_index.get(oid),
        )
        for oid in sorted(
            config_by_index.keys() | measurements_by_index.keys(),
            key=lambda oid: tuple(map(int, oid.split("."))),
        )
    )
    labels = [[str(oid), str(label)] for oid, label in string_table[2]]
    lines = [[str(oid), str(line)] for oid, line in string_table[3]]
    electrical = {}
    electrical_error = None
    try:
        electrical = parse_electrical_section(
            sensors, labels, lines, connector_kind="Outlet", poles=True,
        )
    except (ValueError, OverflowError) as exc:
        electrical_error = f"{type(exc).__name__}: {exc}"
    return Section(sensors=sensors, electrical=electrical, electrical_error=electrical_error)


snmp_section_raritan_pdu_outlet = SNMPSection(
    name="raritan_pdu_outlet",
    detect=DETECT_RARITAN,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.5.6.1",  # outletPoleSensorConfigurationEntry
            oids=[
                OIDEnd(),  # PDU.connector[.pole].sensorType
                "6",  # units; 2 = amperes
                "7",  # decimal digits
                "23",  # unsigned upper critical threshold
                "24",  # unsigned upper warning threshold
                OIDBytes("25"),  # enabled lower/upper warning/critical thresholds
                "27",  # signed minimum; negative selects signed readings and limits
                "30",  # signed upper critical threshold
                "31",  # signed upper warning threshold
                "21",  # unsigned lower critical threshold
                "22",  # unsigned lower warning threshold
                "28",  # signed lower critical threshold
                "29",  # signed lower warning threshold
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.5.4.4.1",  # outletPoleSensorMeasurementsEntry
            oids=[
                OIDEnd(),  # PDU.connector[.pole].sensorType
                "2",  # availability
                "3",  # state
                "4",  # unsigned measurement
                "6",  # signed measurement
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.5.3.1",  # outletConfigurationEntry
            oids=[
                OIDEnd(),  # PDU.connector
                "2",  # outletLabel
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.5.5.1",  # outletPoleConfigurationEntry
            oids=[
                OIDEnd(),  # PDU.connector.pole
                "1",  # outletPoleLine: 1=L1, 2=L2, 3=L3, 4=N, 5=DC+, 6=DC-
            ],
        ),
    ],
    parse_function=parse_raritan_pdu_outlet,
)

check_plugin_raritan_pdu_outlet_poles = CheckPlugin(
    name="raritan_pdu_outlet_poles",
    sections=["raritan_pdu_outlet"],
    service_name="Outlet %s",
    discovery_function=discover_pdu_electrical,
    check_function=check_pdu_electrical,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)

#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, List, Mapping, Union

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    all_of,
    any_of,
    check_levels,
    contains,
    exists,
    get_value_store,
    OIDCached,
    OIDEnd,
    register,
    Result,
    Service,
    SNMPTree,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.cisco_sensor_item import cisco_sensor_item
from cmk.base.plugins.agent_based.utils.temperature import check_temperature, TempParamDict

Section = Mapping[str, Mapping[str, Mapping[str, Any]]]  # oh boy.

_Levels = Union[None, tuple[float, float, float, float], tuple[float, float]]

# NOTE: Devices of type 3850 with firmware versions 3.2.0SE, 3.2.1, 3.2.2
# have been observed to display a tenth of the actual temperature value.
# A firmware update on the device fixes this.

# NOTE: But, in 2020/2021:
# Wrong values for transceivers (DOM) in C9500-24Y4C and C9500-48Y4C CSCvt16172
# The bug link: https://bst.cloudapps.cisco.com/bugsearch/bug/CSCvt16172
#
# See: SUP-4746
#

# OID: ifAdminStatus
_CISCO_TEMPERATURE_ADMIN_STATE_MAP = {
    "1": "up",
    "2": "down",
    "3": "testing",
}


def parse_cisco_temperature(  # pylint: disable=too-many-branches
    string_table: List[StringTable],
) -> Section:
    # CISCO-ENTITY-SENSOR-MIB entSensorType
    cisco_sensor_types = {
        "1": "other",
        "2": "unknown",
        "3": "voltsAC",
        "4": "voltsDC",
        "5": "amperes",
        "6": "watts",
        "7": "hertz",
        "8": "celsius",
        "9": "parentRH",
        "10": "rpm",
        "11": "cmm",
        "12": "truthvalue",
        "13": "specialEnum",
        "14": "dBm",
    }

    # CISCO-ENTITY-SENSOR-MIB::entSensorScale
    cisco_entity_exponents = {
        "1": -24,  # yocto
        "2": -21,  # zepto
        "3": -18,  # atto
        "4": -15,  # femto
        "5": -12,  # pico
        "6": -9,  # nano
        "7": -6,  # micro
        "8": -3,  # milli
        "9": 0,  # units
        "10": 3,  # kilo
        "11": 6,  # mega
        "12": 9,  # giga
        "13": 12,  # tera
        "14": 18,  # exa
        "15": 15,  # peta
        "16": 21,  # zetta
        "17": 24,  # yotta
    }

    # CISCO-ENTITY-SENSOR-MIB::entSensorStatus
    map_states = {
        "1": (0, "OK"),
        "2": (3, "unavailable"),
        "3": (3, "non-operational"),
    }

    # CISCO-ENVMON-MIB
    map_envmon_states = {
        "1": (0, "normal"),
        "2": (1, "warning"),
        "3": (2, "critical"),
        "4": (2, "shutdown"),
        "5": (3, "not present"),
        "6": (2, "not functioning"),
    }

    # description_info = [...,
    #                     [u'25955', u'Ethernet1/9(Rx-dBm)'],
    #                     [u'25956', u'Ethernet1/9(Tx-dBm)'],
    #                     ...]
    # state_info = [...,
    #               [u'25955', u'14', u'8', u'0', u'-3487', u'1'],
    #               [u'25956', u'14', u'8', u'0', u'-2525', u'1'],
    #               ...]
    # admin_states = [['Ethernet1/9', '1'], ...]
    #

    # IMPORTANT HINT: Temperature sensors uniquely identified via the indices in
    # description_info and linked to data in state_info are different sensors than
    # the ones contained in the perfstuff data structure. Sensors contained in the
    # perfstuff data structure contain only one threshold value for temperature.
    #
    # description_info = [...,
    #                     [u'1008', u'Switch 1 - WS-C2960X-24PD-L - Sensor 0'],
    #                     ...,
    #                     [u'2008', u'Switch 2 - WS-C2960X-24PD-L - Sensor 0'],
    #                     ...]
    # perfstuff = [...,
    #              [u'1008', u'SW#1, Sensor#1, GREEN', u'36', u'68', u'1'],
    #              [u'2008', u'SW#2, Sensor#1, GREEN', u'37', u'68', u'1'],
    #              ...]

    description_info, state_info, levels_info, perfstuff, admin_states = string_table

    # Create dict of sensor descriptions
    descriptions = dict(description_info)

    # Map admin state of Ethernet ports to sensor_ids of corresponding ethernet port sensors.
    # E.g. Ethernet1/9 -> Ethernet1/9(Rx-dBm), Ethernet1/9(Tx-dBm)
    # In case the description has been modified in the switch device this
    # mapping will not be successful. The description contains an ID instead of
    # a human readable string to identify the sensors then. The sensors cannot
    # be looked up in the description_info then.
    admin_states_dict = {}
    for if_name, admin_state in admin_states:
        for sensor_id, descr in descriptions.items():
            if descr.startswith(if_name):
                admin_states_dict[sensor_id] = _CISCO_TEMPERATURE_ADMIN_STATE_MAP.get(admin_state)

    # Create dict with thresholds
    thresholds: dict[str, list[str]] = {}
    for sensor_id, sensortype_id, scalecode, magnitude, value, sensorstate in state_info:
        thresholds.setdefault(sensor_id, [])

    for endoid, level in levels_info:
        # endoid is e.g. 21549.9 or 21459.10
        sensor_id, _subid = endoid.split(".")
        thresholds.setdefault(sensor_id, []).append(level)

    # Parse OIDs described by CISCO-ENTITY-SENSOR-MIB
    entity_parsed: dict[str, dict[str, dict[str, str]]] = {}
    for sensor_id, sensortype_id, scalecode, magnitude, value, sensorstate in state_info:
        sensortype = cisco_sensor_types.get(sensortype_id)
        if sensortype not in ("dBm", "celsius"):
            continue

        if sensor_id in descriptions:
            descr = descriptions[sensor_id]
        else:
            descr = sensor_id

        if not descr:
            continue

        entity_parsed.setdefault(sensortype_id, {})

        sensor_attrs: dict[str, Any] = {
            "descr": descr,
            "raw_dev_state": sensorstate,  # used in discovery function
            "dev_state": map_states.get(sensorstate, (3, "unknown[%s]" % sensorstate)),
            "admin_state": admin_states_dict.get(sensor_id),
        }

        if sensorstate == "1":
            factor = 10.0 ** (float(cisco_entity_exponents[scalecode]) - float(magnitude))
            sensor_attrs["reading"] = float(value) * factor
            # All sensors have 4 threshold values.
            # Map thresholds [crit_upper, warn_upper, crit_lower, warn_lower] to
            # dev_levels (warn_upper, crit_upper, warn_lower, crit_lower) conform
            # with check_levels() signature.
            # e.g. [u'75000', u'70000', u'-5000', u'0'] -> (70000, 75000, 0, -5000)
            # For temperature sensors only the upper levels are considered.
            # e.g. [u'75000', u'70000, u'-5000', u'0'] -> (70000, 75000)
            # In case devices do no validation when thresholds are set this could result
            # in threshold values in a wrong order. To keep the behaviour consistent
            # to temperature sensors the device levels are ordered accoringly.
            if sensortype == "dBm" and len(thresholds[sensor_id]) == 4:
                unsorted_thresholds = thresholds[sensor_id][0:4]
                converted_thresholds = [float(t) * factor for t in unsorted_thresholds]
                sorted_thresholds = sorted(converted_thresholds, key=float)
                opt_crit_upper, opt_warn_upper, opt_crit_lower, opt_warn_lower = (
                    sorted_thresholds[3],
                    sorted_thresholds[2],
                    sorted_thresholds[0],
                    sorted_thresholds[1],
                )
                dev_levels: _Levels = (
                    opt_warn_upper,
                    opt_crit_upper,
                    opt_warn_lower,
                    opt_crit_lower,
                )
            elif sensortype == "celsius" and len(thresholds[sensor_id]) == 4:
                temp_crit_upper_raw, temp_warn_upper_raw = thresholds[sensor_id][0:2]
                # Some devices deliver these values in the wrong order. In case the devices
                # do no validation when thresholds are set this could result in values in a
                # wrong oder as well. Device levels are assigned accoring to their size.
                dev_levels = (
                    min(float(temp_warn_upper_raw) * factor, float(temp_crit_upper_raw) * factor),
                    max(float(temp_warn_upper_raw) * factor, float(temp_crit_upper_raw) * factor),
                )
            else:
                dev_levels = None
            sensor_attrs["dev_levels"] = dev_levels
            entity_parsed[sensortype_id].setdefault(sensor_id, sensor_attrs)

    found_temp_sensors = entity_parsed.get("8", {})
    parsed: dict[str, dict[str, dict[str, Any]]] = {}
    temp_sensors = parsed.setdefault("8", {})
    for sensor_id, statustext, temp, max_temp, state in perfstuff:
        if sensor_id in descriptions and sensor_id in found_temp_sensors:
            # if this sensor is already in the dictionary, ensure we use the same name
            item = descriptions[sensor_id]
            prev_description = cisco_sensor_item(statustext, sensor_id)
            # also register the name we would have used up to 1.2.8b4, so we can give
            # the user a proper info message.
            # It's the little things that show you care
            temp_sensors[prev_description] = {"obsolete": True}
        else:
            item = cisco_sensor_item(statustext, sensor_id)

        temp_sensor_attrs: dict[str, Any] = {
            "raw_dev_state": state,
            "dev_state": map_envmon_states.get(state, (3, "unknown[%s]" % state)),
        }

        try:
            temp_sensor_attrs["reading"] = int(temp)
            if max_temp and int(max_temp):
                temp_sensor_attrs["dev_levels"] = (int(max_temp), int(max_temp))
            else:
                temp_sensor_attrs["dev_levels"] = None
        except Exception:
            temp_sensor_attrs["dev_state"] = (3, "sensor defect")

        temp_sensors.setdefault(item, temp_sensor_attrs)

    for sensor_type, sensors in entity_parsed.items():
        for sensor_attrs in sensors.values():
            # Do not overwrite found sensors from perfstuff loop
            parsed.setdefault(sensor_type, {}).setdefault(sensor_attrs["descr"], sensor_attrs)

    return parsed


register.snmp_section(
    name="cisco_temperature",
    parse_function=parse_cisco_temperature,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"),
        any_of(
            exists(".1.3.6.1.4.1.9.9.91.1.1.1.1.*"),
            exists(".1.3.6.1.4.1.9.9.13.1.3.1.3.*"),
        ),
    ),
    fetch=[
        # cisco_temp_sensor data
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[
                OIDEnd(),
                OIDCached("7"),  # Name of the sensor
            ],
        ),
        # Type and current state
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.91.1.1.1.1",
            oids=[
                OIDEnd(),
                "1",  # CISCO-ENTITY-SENSOR-MIB::entSensorType
                "2",  # CISCO-ENTITY-SENSOR-MIB::entSensorScale
                "3",  # CISCO-ENTITY-SENSOR-MIB::entSensorPrecision
                "4",  # CISCO-ENTITY-SENSOR-MIB::entSensorValue
                "5",  # CISCO-ENTITY-SENSOR-MIB::entSensorStatus
            ],
        ),
        # Threshold
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.91.1.2.1.1",
            oids=[
                OIDEnd(),
                "4",  # Thresholds
            ],
        ),
        # cisco_temp_perf data
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.13.1.3.1",
            oids=[  # CISCO-SMI
                OIDEnd(),
                "2",  # ciscoEnvMonTemperatureStatusDescr
                "3",  # ciscoEnvMonTemperatureStatusValue
                "4",  # ciscoEnvMonTemperatureThreshold
                "6",  # ciscoEnvMonTemperatureState
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[
                OIDCached("2"),  # Description of the sensor
                OIDCached("7"),  # ifAdminStatus
            ],
        ),
    ],
)


#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_cisco_temperature(section: Section) -> DiscoveryResult:
    for item, value in section.get("8", {}).items():
        if not value.get("obsolete", False):
            yield Service(item=item)


def check_cisco_temperature(item: str, params: TempParamDict, section: Section) -> CheckResult:
    temp_parsed = section.get("8", {})
    if item not in temp_parsed:
        return

    data = temp_parsed[item]
    if data.get("obsolete", False):
        yield Result(state=State.UNKNOWN, summary="This sensor is obsolete, please rediscover")
        return

    state, state_readable = data["dev_state"]
    reading = data.get("reading")
    if reading is None:
        yield Result(state=State(state), summary="Status: %s" % state_readable)
        return

    yield from check_temperature(
        reading,
        params,
        unique_name="cisco_temperature_%s" % item,
        value_store=get_value_store(),
        dev_levels=data["dev_levels"],
        dev_status=state,
        dev_status_name=state_readable,
    )


register.check_plugin(
    name="cisco_temperature",
    service_name="Temperature %s",
    discovery_function=discover_cisco_temperature,
    check_function=check_cisco_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={},  # is this OK?
)

# .
#   .--dom-----------------------------------------------------------------.
#   |                            _                                         |
#   |                         __| | ___  _ __ ___                          |
#   |                        / _` |/ _ \| '_ ` _ \                         |
#   |                       | (_| | (_) | | | | | |                        |
#   |                        \__,_|\___/|_| |_| |_|                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | digital optical monitoring                                           |
#   '----------------------------------------------------------------------'


def discover_cisco_temperature_dom(params: Mapping[str, Any], section: Section) -> DiscoveryResult:
    parsed_dom = section.get("14", {})
    admin_states_to_discover = {
        _CISCO_TEMPERATURE_ADMIN_STATE_MAP[admin_state]
        for admin_state in params.get("admin_states", ["1"])
    } | {None}
    for item, attrs in parsed_dom.items():
        dev_state = attrs.get("raw_dev_state")
        adm_state = attrs.get("admin_state")
        if dev_state == "1" and adm_state in admin_states_to_discover:
            yield Service(item=item)


def _determine_levels(
    user_levels: tuple[float, float] | bool,
    device_levels: tuple[float, float] | tuple[None, None],
) -> tuple[float, float] | None:
    if isinstance(user_levels, tuple):
        return user_levels
    if user_levels:
        if device_levels[0] is None or device_levels[1] is None:
            return None
        return device_levels
    return None


def check_cisco_temperature_dom(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    # TODO perf, precision, severity, etc.

    data = section.get("14", {}).get(item, {})
    reading = data.get("reading")
    if reading is None:
        return

    # TODO: care about check status which is always OK
    state, state_readable = data["dev_state"]
    yield Result(state=State(state), summary="Status: %s" % state_readable)

    # get won't save you, because 'dev_levels' may be present, but None.
    device_levels = data.get("dev_levels") or (None, None, None, None)

    if "Transmit" in data["descr"]:
        dsname = "output_signal_power_dbm"
    elif "Receive" in data["descr"]:
        dsname = "input_signal_power_dbm"
    else:
        # in rare case of sensor id instead of sensor description no destinction
        # between transmit/receive possible
        dsname = "signal_power_dbm"
    yield from check_levels(
        reading,
        metric_name=dsname,
        # Map WATO configuration of levels to check_levels() compatible tuple.
        # Default value in case of missing WATO config is use device levels.
        levels_lower=_determine_levels(params.get("power_levels_lower", True), device_levels[2:4]),
        levels_upper=_determine_levels(params.get("power_levels_upper", True), device_levels[0:2]),
        render_func=lambda f: "%.2f dBm" % f,
        label="Signal power",
    )


register.check_plugin(
    name="cisco_temperature_dom",
    service_name="DOM %s",
    sections=["cisco_temperature"],
    discovery_function=discover_cisco_temperature_dom,
    discovery_default_parameters={"admin_states": ["1"]},
    discovery_ruleset_name="discovery_cisco_dom_rules",
    check_function=check_cisco_temperature_dom,
    check_ruleset_name="cisco_dom",
    check_default_parameters={},
)

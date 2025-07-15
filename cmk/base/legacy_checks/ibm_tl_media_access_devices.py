#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, SNMPTree, startswith
from cmk.base.check_legacy_includes.ibm_tape_library import (
    ibm_tape_library_get_device_state,
    ibm_tape_library_parse_device_name,
)

check_info = {}

# .1.3.6.1.4.1.14851.3.1.6.2.1.2.1 3 --> SNIA-SML-MIB::mediaAccessDeviceObjectType.1
# .1.3.6.1.4.1.14851.3.1.6.2.1.2.2 3 --> SNIA-SML-MIB::mediaAccessDeviceObjectType.2
# .1.3.6.1.4.1.14851.3.1.6.2.1.3.1 IBM     ULT3580-TD6     00078B5F0F --> SNIA-SML-MIB::mediaAccessDevice-Name.1
# .1.3.6.1.4.1.14851.3.1.6.2.1.3.2 IBM     ULT3580-TD6     00078B5FCF --> SNIA-SML-MIB::mediaAccessDevice-Name.2
# .1.3.6.1.4.1.14851.3.1.6.2.1.6.1 2 --> SNIA-SML-MIB::mediaAccessDevice-NeedsCleaning.1
# .1.3.6.1.4.1.14851.3.1.6.2.1.6.2 2 --> SNIA-SML-MIB::mediaAccessDevice-NeedsCleaning.2

# .1.3.6.1.4.1.14851.3.1.12.2.1.3.1 IBM     ULT3580-TD6     00078B5F0F --> SNIA-SML-MIB::scsiProtocolController-ElementName.1
# .1.3.6.1.4.1.14851.3.1.12.2.1.3.2 IBM     ULT3580-TD6     00078B5FCF --> SNIA-SML-MIB::scsiProtocolController-ElementName.2
# .1.3.6.1.4.1.14851.3.1.12.2.1.4.1 2 --> SNIA-SML-MIB::scsiProtocolController-OperationalStatus.1
# .1.3.6.1.4.1.14851.3.1.12.2.1.4.2 2 --> SNIA-SML-MIB::scsiProtocolController-OperationalStatus.2
# .1.3.6.1.4.1.14851.3.1.12.2.1.6.1 3 --> SNIA-SML-MIB::scsiProtocolController-Availability.1
# .1.3.6.1.4.1.14851.3.1.12.2.1.6.2 3 --> SNIA-SML-MIB::scsiProtocolController-Availability.2


def parse_ibm_tl_media_access_devices(string_table):
    parsed = {}
    media_access_info, controller_info = string_table
    for ty, name, clean in media_access_info:
        parsed.setdefault(
            ibm_tape_library_parse_device_name(name),
            {
                "type": {
                    "0": "unknown",
                    "1": "worm drive",
                    "2": "magneto optical drive",
                    "3": "tape drive",
                    "4": "dvd drive",
                    "5": "cdrom drive",
                }[ty],
                "clean": {
                    "0": "unknown",
                    "1": "true",
                    "2": "false",
                }[clean],
            },
        )

    for ctrl_name, ctrl_avail, ctrl_status in controller_info:
        ctrl_name = ibm_tape_library_parse_device_name(ctrl_name)
        if ctrl_name in parsed:
            parsed[ctrl_name]["ctrl_avail"] = ctrl_avail
            parsed[ctrl_name]["ctrl_status"] = ctrl_status

    return parsed


def inventory_ibm_tl_media_access_devices(parsed):
    for device in parsed:
        yield device, None


def check_ibm_tl_media_access_devices(item, params, parsed):
    if item in parsed:
        data = parsed[item]
        if data.get("ctrl_avail") and data.get("ctrl_status"):
            yield from ibm_tape_library_get_device_state(data["ctrl_avail"], data["ctrl_status"])
        yield 0, "Type: {}, Needs cleaning: {}".format(data["type"], data["clean"])


check_info["ibm_tl_media_access_devices"] = LegacyCheckDefinition(
    name="ibm_tl_media_access_devices",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.32925.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2.6.254"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.14851.3.1.6.2.1",
            oids=["2", "3", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.14851.3.1.12.2.1",
            oids=["3", "6", "4"],
        ),
    ],
    parse_function=parse_ibm_tl_media_access_devices,
    service_name="Media access device %s",
    discovery_function=inventory_ibm_tl_media_access_devices,
    check_function=check_ibm_tl_media_access_devices,
)

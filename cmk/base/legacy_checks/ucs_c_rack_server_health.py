#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# exemplary output of special agent agent_ucs_bladecenter (<TAB> is tabulator):
# storageControllerHealth<TAB>dn
# sys/rack-unit-1/board/storage-SAS-SLOT-HBA/vd-0 <TAB>id SLOT-HBA<TAB>health Good
# storageControllerHealth<TAB>dn
# sys/rack-unit-2/board/storage-SAS-SLOT-HBA/vd-0 <TAB>id SLOT-HBA<TAB>health Good


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_ucs_c_rack_server_health(string_table):
    """
    Input: list of lists containing storage controller health data on a per rack basis.
    Output: Returns dict with indexed Rack Units mapped to keys and lowercase health string mapped to value
    'health' if rack server has racks attached or empty dict if not.
    """
    parsed = {}
    for _, dn, _id, health in string_table:
        rack_storage_board = (
            dn.replace("dn sys/", "")
            .replace("rack-unit-", "Rack unit ")
            .replace("/board/storage-", " Storage ")
            .replace("-", " ")
            .replace("/", " ")
        )
        parsed[rack_storage_board] = health.replace("health ", "").lower()
    return parsed


def discover_ucs_c_rack_server_health(parsed):
    """
    Input: dict containing items as keys or empty dict.
    Output: Yields indexed racks and storage controllers as items (e.g. Rack Unit 1 Storage SAS SLOT HBA vd 0) in case parsed contains items.
    """
    for key in parsed:
        yield key, {}


def check_ucs_c_rack_server_health(item, params, parsed):
    """
    Check function is called only in case parsed is a dict and item exists as key in parsed[item].
    All other potential bad case conditions are handled by @get_parsed_item_data.
    """
    if not (health := parsed.get(item)):
        return
    # Dict keys are storage controller health strings provided via special agent -> XML
    # API of servers. Dict values are corresponding check status.
    # For information about the data provided by the special agent
    # "storageControllerHealth" refer to Cisco C-Series Rack Server XML 2.0 Schema files:
    # [https://community.cisco.com/t5/unified-computing-system/cisco-ucs-c-series-standalone-xml-schema/ta-p/3646798]
    # Note: The possible string values are not defined/documented in the XML schema.
    # "Good" is the only value known from exemplary data output. Pre-process the
    # data to lowercase only chars.
    health_to_status_mapping = {
        "good": 0,
    }

    try:
        status = health_to_status_mapping[health]
        status_readable = health
    except KeyError:
        status = 3
        status_readable = "unknown[%s]" % health
    yield status, "Status: %s" % status_readable


check_info["ucs_c_rack_server_health"] = LegacyCheckDefinition(
    name="ucs_c_rack_server_health",
    parse_function=parse_ucs_c_rack_server_health,
    service_name="Health %s",
    discovery_function=discover_ucs_c_rack_server_health,
    check_function=check_ucs_c_rack_server_health,
)

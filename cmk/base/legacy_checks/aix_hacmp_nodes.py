#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def parse_aix_hacmp_nodes(string_table):
    parsed = {}
    for line in string_table:
        if len(line) == 1:
            parsed[line[0]] = {}

        elif "node" in line[0].lower():
            if line[1].replace(":", "") in parsed:
                node_name = line[1].replace(":", "")
                get_details = True
            else:
                get_details = False

        elif "Interfaces" in line[0] and get_details:
            network_name = line[3].replace(",", "")
            parsed[node_name][network_name] = []

        elif "Communication" in line[0] and get_details:
            parsed[node_name][network_name].append(
                (
                    line[3].replace(",", ""),
                    line[5].replace(",", ""),
                    line[8].replace(",", ""),
                )
            )

    return parsed


def inventory_aix_hacmp_nodes(parsed):
    return [(key, None) for key in parsed]


def check_aix_hacmp_nodes(item, _no_params, parsed):
    if item in parsed:
        for network_name in parsed[item]:
            infotext = "Network: %s" % network_name

            for if_name, attribute, ip_adr in parsed[item][network_name]:
                infotext += f", interface: {if_name}, attribute: {attribute}, IP: {ip_adr}"

            return 0, infotext
    return None


check_info["aix_hacmp_nodes"] = LegacyCheckDefinition(
    parse_function=parse_aix_hacmp_nodes,
    service_name="HACMP Node %s",
    discovery_function=inventory_aix_hacmp_nodes,
    check_function=check_aix_hacmp_nodes,
)

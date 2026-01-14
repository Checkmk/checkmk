#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"


# <<<scaleio_mdm:sep(44)>>>
# Cluster:
#    Mode: 3_node, State: Normal, Active: 3/3, Replicas: 2/2
#    Virtual IPs: N/A
# Master MDM:
#    Name: MDM02, ID: 0x028f4e581a749941
#        IPs: 10.75.9.52, 10.75.10.52, Management IPs: 10.75.0.52, Port: 9011, Virtual IP interfaces: N/A
#        Version: 2.0.13000
# Slave MDMs:
#    Name: MDM01, ID: 0x1402b04f3ad359c0
#        IPs: 10.75.10.51, 10.75.9.51, Management IPs: 10.75.0.51, Port: 9011, Virtual IP interfaces: N/A
#        Status: Normal, Version: 2.0.13000
# Tie-Breakers:
#    Name: TB01, ID: 0x69dd57a10fa1c7b2
#        IPs: 10.75.10.53, 10.75.9.53, Port: 9011
#        Status: Normal, Version: 2.0.13000


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def add_key_values(data_dict, line):
    """
    Finally we can add the rest of information to a node in a
    subsection. When splitting the lines we sometimes get lines
    belonging to the last entry. These information is then added
    to the last known entry.
    """
    for token in (entry.split(": ") for entry in line):
        if len(token) > 1:
            name = token[0].strip()
            data_dict[name] = token[1].strip()
        else:
            if not isinstance(data_dict[name], list):
                data_dict[name] = [data_dict[name]]
            data_dict[name].append(token[0].replace(" ", ""))


def parse_scaleio_mdm(string_table):
    # parsing this section is horrible. But I will guide you...
    parsed, id_, node = {}, "", ""
    for line in string_table:
        # A subsection starts with one of the following:
        if line[0].lower() in (
            "cluster:",
            "master mdm:",
            "slave mdms:",
            "tie-breakers:",
            "standby mdms:",
        ):
            id_ = line[0].strip(":")
            data = parsed.setdefault(id_, {})
            continue
        if id_ not in parsed:
            continue

        # The first subsection is different and entries can be parsed
        # directly. Hooray!
        if id_ == "Cluster":
            add_key_values(data, line)
        # The other subsections can have several nodes. Each node
        # starts with his name and has already some more information.
        # Sometimes there is information about a role inside of the
        # cluster. This is handled by the entry "Role"!
        elif "name" in line[0].lower():
            node = line[0].split(": ")[1]
            node_id = line[1].split(": ")

            data[node] = {node_id[0].strip(): node_id[1].strip()}
            if len(line) == 3:
                data[node]["Role"] = line[2].strip()
        elif node in data:
            add_key_values(data[node], line)

    return parsed


def discover_scaleio_mdm(parsed):
    if parsed.get("Cluster"):
        yield None, {}


def check_scaleio_mdm(_no_item, _no_params, parsed):
    translate_status = {
        "Normal": 0,
        "Degraded": 1,
        "Error": 2,
        "Disconnected": 2,
        "Not synchronized": 1,
    }

    data = parsed.get("Cluster")
    if data:
        state = 0
        status = data["State"]
        active = data["Active"].split("/")
        replicas = data["Replicas"].split("/")

        yield translate_status[status], "Mode: {}, State: {}".format(data["Mode"], status)

        if not active[0] == active[1] or not replicas[0] == replicas[1]:
            state = 2

        yield state, "Active: {}, Replicas: {}".format("/".join(active), "/".join(replicas))

    for role in ["Master MDM", "Slave MDMs", "Tie-Breakers", "Standby MDMs"]:
        state, nodes = 0, []
        for node in sorted(parsed.get(role, {})):
            nodes.append(node)
            status = parsed[role][node].get("Status", "Normal")
            if status != "Normal":
                state = max(state, translate_status[status])

        if nodes:
            infotext = "{}: {}".format(role, ", ".join(nodes))
        elif role != "Standby MDMs":
            state, infotext = 2, "%s not found in agent output" % role
        else:
            infotext = "%s: no" % role

        yield state, infotext


check_info["scaleio_mdm"] = LegacyCheckDefinition(
    name="scaleio_mdm",
    parse_function=parse_scaleio_mdm,
    service_name="ScaleIO cluster status",
    discovery_function=discover_scaleio_mdm,
    check_function=check_scaleio_mdm,
)

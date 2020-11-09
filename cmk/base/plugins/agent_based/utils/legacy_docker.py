#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import List

import json


class DeprecatedDict(dict):
    pass


class DeprecatedList(list):
    pass


def legacy_map_keys(dictionary, map_keys):
    for old, new in map_keys:
        if old in dictionary:
            dictionary[new] = dictionary.pop(old)


def parse_node_info(info):  # pylint: disable=too-many-branches
    '''parse output of "docker info"'''
    parsed = DeprecatedDict()
    if not info:
        return parsed

    # parse legacy json output (verisons 1.5.0 - 1.5.0p6)
    joined = " ".join(info[0])
    if joined.endswith("permission denied"):
        return parsed
    try:
        # this may contain a certificate containing newlines.
        return json.loads(joined.replace("\n", "\\n"))
    except ValueError:
        pass

    # changes in 19.03.01
    start_index = 0
    if info[0][0] == "|Client":
        try:
            start_index = info.index(["|Server", ""]) + 1
        except ValueError:
            pass

    prefix = ""
    for row in info[start_index:]:
        if not row:
            continue
        # remove '|', it was protecting leading whitespace
        row0 = row[0][1:]
        if not row0:
            continue
        # ignore misssing keys / pad lines that are not of "key: value" type
        if len(row) == 1:
            row.append('')
        key = row0.strip()
        value = ':'.join(row[1:]).strip()
        # indented keys are prefixed by the last not indented key
        if len(row0) - len(key) == 0:
            parsed[key] = value
            prefix = key
        else:
            parsed[prefix + key] = value

    # changes in 19.03.01
    legacy_map_keys(parsed, (("Running", "ContainersRunning"), ("Stopped", "ContainersStopped"),
                             ("Paused", "ContainersPaused"), ("Managers", "SwarmManagers"),
                             ("NodeID", "SwarmNodeID")))

    # some modifications to match json output:
    for key in ("Images", "Containers", "ContainersRunning", "ContainersStopped",
                "ContainersPaused"):
        try:
            parsed[key] = int(parsed[key])
        except (KeyError, ValueError):
            pass
    # reconstruct labels (they where not in "k: v" format)
    parsed["Labels"] = []
    for k in sorted(parsed):  # pylint: disable=consider-iterating-dictionary
        if k.startswith("Labels") and k != "Labels":
            parsed["Labels"].append(k[6:] + parsed.pop(k))
    # reconstruct swarm info:
    if "Swarm" in parsed:
        swarm = {"LocalNodeState": parsed["Swarm"]}
        if "SwarmNodeID" in parsed:
            swarm["NodeID"] = parsed.pop("SwarmNodeID")
        if "SwarmManagers" in parsed:
            swarm["RemoteManagers"] = parsed.pop("SwarmManagers")
        parsed["Swarm"] = swarm

    if "Server Version" in parsed:
        parsed["ServerVersion"] = parsed.pop("Server Version")
    if "Registry" in parsed:
        parsed["IndexServerAddress"] = parsed.pop("Registry")

    return parsed


def parse_network_inspect(info: List[List[str]]) -> List:
    try:
        networks = json.loads(''.join(row[0] for row in info if row))
    except ValueError:
        return []
    assert isinstance(networks, list)
    return networks

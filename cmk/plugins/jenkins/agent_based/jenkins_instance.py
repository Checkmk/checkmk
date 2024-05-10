#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<jenkins_instance>>>
# {"quietingDown": false, "nodeDescription": "the master Jenkins node",
# "numExecutors": 0, "mode": "NORMAL", "_class": "hudson.model.Hudson",
# "useSecurity": true}

import json
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

MAP_INSTANCE_STATE = {
    True: "yes",
    False: "no",
    "NORMAL": "normal",
    "EXCLUSIVE": "exclusive",
    None: "N/A",
}


class JenkinsInstance(TypedDict, total=False):
    nodeDescription: str
    quietingDown: bool
    useSecurity: bool


def parse_jenkins_instance(string_table: StringTable) -> JenkinsInstance:
    parsed: JenkinsInstance = {}

    for line in string_table:
        parsed.update(json.loads(line[0]))

    return parsed


agent_section_jenkins_instance = AgentSection(
    name="jenkins_instance",
    parse_function=parse_jenkins_instance,
)


def inventory_jenkins_instance(section: JenkinsInstance) -> DiscoveryResult:
    yield Service()


def check_jenkins_instance(params: dict, section: JenkinsInstance) -> CheckResult:
    if not section:
        return

    if (instance_description := section.get("nodeDescription")) is not None:
        if not isinstance(instance_description, str):
            instance_description = str(instance_description)

        yield Result(state=State.OK, summary=f"Description: {instance_description.title()}")

    for key, desired_value, infotext in [
        ("quietingDown", False, "Quieting Down"),
        ("useSecurity", True, "Security used"),
    ]:
        state = State.OK
        parsed_data = section.get(key)
        assert isinstance(parsed_data, bool), f"Expected boolean value for {key}"

        if parsed_data is not None and parsed_data != desired_value:
            state = State.WARN
        elif parsed_data is None:
            state = State.UNKNOWN

        yield Result(state=state, summary=f"{infotext}: {MAP_INSTANCE_STATE[parsed_data]}")


check_plugin_jenkins_instance = CheckPlugin(
    name="jenkins_instance",
    service_name="Jenkins Instance",
    discovery_function=inventory_jenkins_instance,
    check_function=check_jenkins_instance,
    check_default_parameters={},
)

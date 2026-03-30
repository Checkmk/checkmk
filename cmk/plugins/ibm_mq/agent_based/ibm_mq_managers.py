#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.ibm.agent_based.ibm_mq_managers import Section
from cmk.plugins.ibm_mq.lib import ibm_mq_check_version

# <<<ibm_mq_managers:sep(10)>>>
# QMNAME(QMIMIQ11) STATUS(RUNNING) DEFAULT(NO) STANDBY(PERMITTED) INSTNAME(Installation1) INSTPATH(/usr/mqm) INSTVER(8.0.0.5)
#     INSTANCE(iasv0001) MODE(Active)
#     INSTANCE(tasv0397) MODE(Standby)

# <<<ibm_mq_managers:sep(10)>>>
# QMNAME(QMIMIQ11) STATUS(RUNNING AS STANDBY) DEFAULT(YES) STANDBY(PERMITTED) INSTNAME(Installation1) INSTPATH(/usr/mqm) INSTVER(8.0.0.5)
#     INSTANCE(iasv0001) MODE(Active)
#     INSTANCE(tasv0397) MODE(Standby)

# <<<ibm_mq_managers:sep(10)>>>
# QMNAME(QMTEMQS02A) STATUS(ENDED IMMEDIATELY) DEFAULT(NO) STANDBY(NOT APPLICABLE) INSTNAME(Installation1) INSTPATH(/usr/mqm) INSTVER(8.0.0.4)
# QMNAME(QMTEMQS02)  STATUS(RUNNING) DEFAULT(YES) STANDBY(NOT PERMITTED) INSTNAME(Installation1) INSTPATH(/usr/mqm) INSTVER(8.0.0.4)
#     INSTANCE(tasv0065) MODE(Active)

_DEFAULT_STATUS_MAP = {
    "STARTING": ("starting", 0),
    "RUNNING": ("running", 0),
    "RUNNING AS STANDBY": ("running_as_standby", 0),
    "RUNNING ELSEWHERE": ("running_elsewhere", 0),
    "QUIESCING": ("quiescing", 0),
    "ENDING IMMEDIATELY": ("ending_immediately", 0),
    # Older MQ-Versions (e.g. 7.5.0.2) use this status
    "ENDING PREEMPTIVELY": ("ending_pre_emptively", 0),
    "ENDING PRE-EMPTIVELY": ("ending_pre_emptively", 0),
    "ENDED NORMALLY": ("ended_normally", 0),
    "ENDED IMMEDIATELY": ("ended_immediately", 0),
    "ENDED UNEXPECTEDLY": ("ended_unexpectedly", 2),
    # Older MQ-Versions (e.g. 7.5.0.2) use this status
    "ENDED PREEMPTIVELY": ("ended_pre_emptively", 1),
    "ENDED PRE-EMPTIVELY": ("ended_pre_emptively", 1),
    # Older MQ-Versions (e.g. 7.5.0.2) use this status
    "NOT AVAILABLE": ("status_not_available", 0),
    "STATUS NOT AVAILABLE": ("status_not_available", 0),
}


def map_ibm_mq_manager_status(status: str, params: Mapping[str, Any]) -> int:
    wato_key, check_state = _DEFAULT_STATUS_MAP.get(status, ("unknown", 3))
    if "mapped_states" in params:
        mapped_states = dict(params["mapped_states"])
        if wato_key in mapped_states:
            check_state = mapped_states[wato_key]
        elif "mapped_states_default" in params:
            check_state = params["mapped_states_default"]
    return check_state


def discover_ibm_mq_managers(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_ibm_mq_managers(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return

    attrs = data.attributes
    status = attrs["STATUS"]
    default = attrs["DEFAULT"]
    instname = attrs["INSTNAME"]
    instpath = attrs["INSTPATH"]
    instversion = attrs["INSTVER"]

    check_state = map_ibm_mq_manager_status(status, params)
    yield Result(state=State(check_state), summary=f"Status: {status}")
    version_state, version_summary = ibm_mq_check_version(instversion, params, "Version")
    yield Result(state=State(version_state), summary=version_summary)
    yield Result(
        state=State.OK, summary=f"Installation: {instpath} ({instname}), Default: {default}"
    )

    standby = attrs["STANDBY"]
    instances = data.instances
    ha = attrs.get("HA")
    if ha == "REPLICATED":
        if len(instances) > 0:
            yield Result(
                state=State.OK,
                summary=f"High availability: replicated, Instance: {instances[0][0]}",
            )
        else:
            yield Result(state=State.OK, summary="High availability: replicated")
    elif standby == "PERMITTED":
        if len(instances) == 2:
            yield Result(
                state=State.OK,
                summary=f"Multi-Instance: {instances[0][0]}={instances[0][1]} and {instances[1][0]}={instances[1][1]}",
            )
        elif len(instances) == 1:
            yield Result(
                state=State.CRIT,
                summary=f"Multi-Instance: {instances[0][0]}={instances[0][1]} and missing partner",
            )
        else:
            yield Result(
                state=State.CRIT, summary="Multi-Instance: unknown instances (%s)" % instances
            )
    elif standby == "NOT PERMITTED":
        if len(instances) == 1:
            yield Result(
                state=State.OK, summary=f"Single-Instance: {instances[0][0]}={instances[0][1]}"
            )
        else:
            yield Result(
                state=State.CRIT, summary="Single-Instance: unknown instances (%s)" % instances
            )
    elif standby == "NOT APPLICABLE":
        if len(instances) != 0:
            yield Result(state=State.CRIT, summary="Unknown instance setup (%s)" % instances)
    else:
        yield Result(state=State.CRIT, summary="Unknown STANDBY state (%s)" % standby)


check_plugin_ibm_mq_managers = CheckPlugin(
    name="ibm_mq_managers",
    service_name="IBM MQ Manager %s",
    discovery_function=discover_ibm_mq_managers,
    check_function=check_ibm_mq_managers,
    check_ruleset_name="ibm_mq_managers",
    check_default_parameters={},
)

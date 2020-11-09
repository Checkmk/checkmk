#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from typing import (
    Any,
    Dict,
    Optional,
)
from .utils import docker, uptime
from .utils.legacy_docker import DeprecatedDict
from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    StringTable,
    CheckResult,
    HostLabelGenerator,
    Parameters,
)
from .agent_based_api.v1 import (
    register,
    Service,
    Result,
    State as state,
    HostLabel,
    IgnoreResults,
)

RESTART_POLICIES_TO_DISCOVER = ("always",)

HEALTH_STATUS_MAP = {
    "healthy": state.OK,
    "starting": state.WARN,
    "unhealthy": state.CRIT,
}


def _is_active_container(section: Dict[str, Any]) -> bool:
    '''return wether container is or should be running'''
    if section.get("Status") == "running":
        return True
    restart_policy_name = section.get("RestartPolicy", {}).get("Name")
    return restart_policy_name in RESTART_POLICIES_TO_DISCOVER


def parse_docker_container_status(string_table: StringTable) -> Dict[str, Any]:
    '''process the first line to a JSON object

    In case there are multiple lines of output sent by the agent only process the first
    line. We assume that this a full JSON object. The rest of the section is skipped.
    When a container got piggyback data from multiple hosts (e.g. a cluster) this results
    in multiple JSON objects handed over to this check.
    '''
    version = docker.get_version(string_table)  # pylint: disable=undefined-variable

    index = 0 if version is None else 1
    section: Dict[str, Any] = {}
    if string_table[index:]:
        section = docker.json_get_obj(string_table[index]) or {}

    if version is None:
        return DeprecatedDict(section)  # pylint: disable=undefined-variable
    return section


def host_labels_docker_container_status(section) -> HostLabelGenerator:
    """
    >>> from pprint import pprint as pp
    >>> list(host_labels_docker_container_status({}))
    [HostLabel('cmk/docker_object', 'container')]
    >>> list(host_labels_docker_container_status({"ImageTags": []}))
    [HostLabel('cmk/docker_object', 'container')]
    >>> pp(list(host_labels_docker_container_status({"ImageTags": ["doctor:strange"]})))
    [HostLabel('cmk/docker_object', 'container'),
     HostLabel('cmk/docker_image', 'doctor:strange'),
     HostLabel('cmk/docker_image_name', 'doctor'),
     HostLabel('cmk/docker_image_version', 'strange')]
    >>> pp(list(host_labels_docker_container_status({"ImageTags": ["fiction/doctor:strange"]})))
    [HostLabel('cmk/docker_object', 'container'),
     HostLabel('cmk/docker_image', 'fiction/doctor:strange'),
     HostLabel('cmk/docker_image_name', 'doctor'),
     HostLabel('cmk/docker_image_version', 'strange')]
    >>> pp(list(host_labels_docker_container_status({"ImageTags": ["library:8080/fiction/doctor"]})))
    [HostLabel('cmk/docker_object', 'container'),
     HostLabel('cmk/docker_image', 'library:8080/fiction/doctor'),
     HostLabel('cmk/docker_image_name', 'doctor')]
    """
    yield HostLabel("cmk/docker_object", "container")

    image_tags = section.get("ImageTags")
    if not image_tags:
        return

    image = image_tags[-1]
    yield HostLabel("cmk/docker_image", "%s" % image)
    if '/' in image:
        __, image = image.rsplit('/', 1)
    if ':' in image:
        image_name, image_version = image.rsplit(':', 1)
        yield HostLabel("cmk/docker_image_name", "%s" % image_name)
        yield HostLabel(u"cmk/docker_image_version", "%s" % image_version)
    else:
        yield HostLabel("cmk/docker_image_name", "%s" % image)


register.agent_section(
    name="docker_container_status",
    parse_function=parse_docker_container_status,
    host_label_function=host_labels_docker_container_status,
)

#.
#   .--Health--------------------------------------------------------------.
#   |                    _   _            _ _   _                          |
#   |                   | | | | ___  __ _| | |_| |__                       |
#   |                   | |_| |/ _ \/ _` | | __| '_ \                      |
#   |                   |  _  |  __/ (_| | | |_| | | |                     |
#   |                   |_| |_|\___|\__,_|_|\__|_| |_|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Represents the containers internal status, as implemented within     |
#   | the container itself using Docker's HEALTHCHECK API                  |
#   '----------------------------------------------------------------------'


def discover_docker_container_status_health(section: Dict[str, Any]) -> DiscoveryResult:
    if not _is_active_container(section):
        return
    # Only discover if a healthcheck and health is configured.
    # Stopped containers may have the 'Health' key anyway, so that's no criteria.
    # Blocked Healthcheck results in Health key not being present
    if {"Healthcheck", "Health"}.issubset(section):
        yield Service()


def check_docker_container_status_health(section: Dict[str, Any]) -> CheckResult:
    if section.get("Status") != "running":
        yield IgnoreResults("Container is not running")
        return

    health = section.get("Health", {})

    health_status = health.get("Status", "unknown")
    cur_state = HEALTH_STATUS_MAP.get(health_status, state.UNKNOWN)
    yield Result(state=cur_state, summary="Health status: %s" % health_status.title())

    last_log = health.get("Log", [{}])[-1]
    # Remove "\n" from health_report string as this would currently raise a value error.
    # This was observed e.g. for the docker_container_status output of check-mk-enterprise:1.6.0p8
    health_report = last_log.get("Output", "no output").strip().replace("\n", ", ")
    if health_report:
        yield Result(state=state(int(last_log.get("ExitCode") != 0)),
                     summary="Last health report: %s" % health_report)

    if cur_state == state.CRIT:
        failing_streak = section.get("Health", {}).get("FailingStreak", "not found")
        yield Result(state=state.CRIT, summary="Failing streak: %s" % failing_streak)

    health_test = section.get("Healthcheck", {}).get("Test")
    if health_test:
        yield Result(state=state.OK, summary="Health test: %s" % ' '.join(health_test))


register.check_plugin(
    name="docker_container_status_health",
    sections=["docker_container_status"],
    service_name="Docker container health",
    discovery_function=discover_docker_container_status_health,
    check_function=check_docker_container_status_health,
)

#   .----------------------------------------------------------------------.
#   |                    ____  _        _                                  |
#   |                   / ___|| |_ __ _| |_ _   _ ___                      |
#   |                   \___ \| __/ _` | __| | | / __|                     |
#   |                    ___) | || (_| | |_| |_| \__ \                     |
#   |                   |____/ \__\__,_|\__|\__,_|___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Represents the status of the docker container "from the outside"     |
#   '----------------------------------------------------------------------'


def discover_docker_container_status(section: Dict[str, Any]):
    if _is_active_container(section):
        yield Service()


def check_docker_container_status(section: Dict[str, Any]) -> CheckResult:
    if isinstance(section, DeprecatedDict):
        yield Result(
            state=state.WARN,
            summary=
            "Deprecated plugin/agent! You are using legacy code, which may lead to crashes and/or incomplete information. Please upgrade the monitored host to use the plugin 'mk_docker.py'."
        )
    status = section.get("Status", "unknown")
    cur_state = {"running": state.OK, "unknown": state.UNKNOWN}.get(status, state.CRIT)

    info = "Container %s" % status
    node_name = section.get("NodeName")
    if node_name:
        info += " on node %s" % node_name

    yield Result(state=cur_state, summary=info)

    if section.get("Error"):
        yield Result(state=state.CRIT, summary="Error: %s" % section["Error"])


register.check_plugin(
    name="docker_container_status",
    service_name="Docker container status",
    discovery_function=discover_docker_container_status,
    check_function=check_docker_container_status,
)

#   .--Uptime--------------------------------------------------------------.
#   |                  _   _       _   _                                   |
#   |                 | | | |_ __ | |_(_)_ __ ___   ___                    |
#   |                 | | | | '_ \| __| | '_ ` _ \ / _ \                   |
#   |                 | |_| | |_) | |_| | | | | | |  __/                   |
#   |                  \___/| .__/ \__|_|_| |_| |_|\___|                   |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
#.


def discover_docker_container_status_uptime(
    section_docker_container_status: Optional[Dict[str, Any]],
    section_uptime: Optional[uptime.Section],
) -> DiscoveryResult:
    if section_uptime:
        for _service in uptime.discover(section_uptime):
            # if the uptime service of the checkmk agent is
            # present, we don't need this service.
            return
    if not section_docker_container_status:
        return
    if _is_active_container(
            section_docker_container_status) and "StartedAt" in section_docker_container_status:
        yield Service()


def check_docker_container_status_uptime(
    params: Parameters,
    section_docker_container_status: Optional[Dict[str, Any]],
    section_uptime: Optional[uptime.Section],
) -> CheckResult:
    if not section_docker_container_status:
        return
    started_str = section_docker_container_status.get("StartedAt")
    if not started_str:
        return

    # assumed format: 2019-06-05T08:58:06.893459004Z
    utc_start = datetime.datetime.strptime(started_str[:-4] + 'UTC', '%Y-%m-%dT%H:%M:%S.%f%Z')

    op_status = section_docker_container_status["Status"]
    if op_status == "running":
        uptime_sec = (datetime.datetime.utcnow() - utc_start).total_seconds()
        yield from uptime.check(params, uptime.Section(int(uptime_sec), None))
    else:
        yield from uptime.check(params, uptime.Section(0, None))
        yield Result(state=state.OK, summary="Operation State: %s" % op_status)


register.check_plugin(
    name="docker_container_status_uptime",
    sections=["docker_container_status", "uptime"],
    service_name="Uptime",
    discovery_function=discover_docker_container_status_uptime,
    check_ruleset_name="uptime",
    check_default_parameters={},
    check_function=check_docker_container_status_uptime,
)

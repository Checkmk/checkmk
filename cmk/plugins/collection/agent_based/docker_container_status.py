#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping
from typing import Any

from dateutil import parser as date_parser

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    HostLabel,
    HostLabelGenerator,
    IgnoreResults,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import docker, uptime

RESTART_POLICIES_TO_DISCOVER = ("always",)

HEALTH_STATUS_MAP = {
    "healthy": State.OK,
    "starting": State.WARN,
    "unhealthy": State.CRIT,
}


SectionStandard = Mapping[str, Any]


Section = SectionStandard | docker.MultipleNodesMarker


def _is_active_container(section: SectionStandard) -> bool:
    """return wether container is or should be running"""
    if section.get("Status") in ("running", "exited"):
        return True
    restart_policy_name = section.get("RestartPolicy", {}).get("Name")
    return restart_policy_name in RESTART_POLICIES_TO_DISCOVER


def parse_docker_container_status(string_table: StringTable) -> Section:
    """Normally, we expect two lines of agent output here: the version information and the section-
    specific JSON data. However, since docker containers are often piggyback hosts, it can happen
    that we get the concatenated agent output from multiple parent hosts in Checkmk (SUP-10582).
    This happens if a container with the same name runs on multiple docker hosts and if the docker
    agent plug-in is configured to use the container name as piggyback host name. Even though this is
    of course unwanted, we 'parse' this data here, s.t. in the check functions, we can inform the user
    about this issue.
    """
    return (
        docker.MultipleNodesMarker()
        if len(docker.cleanup_oci_error_message(string_table)) > 2
        else docker.parse(string_table, strict=False).data
    )


def host_labels_docker_container_status(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:

        cmk/docker_object:container :
            This label is set if the corresponding host is a docker container.

        cmk/docker_image:
            This label is set to the docker image if the corresponding host is
            a docker container.
            For instance: "docker.io/library/nginx:latest"

        cmk/docker_image_name:
            This label is set to the docker image name if the corresponding host
            is a docker container. For instance: "nginx".

        cmk/docker_image_version:
            This label is set to the docker images version if the corresponding
            host is a docker container. For instance: "latest".

    Examples:

        >>> from pprint import pprint
        >>> def show(gen):
        ...     for l in gen: print(':'.join(l))
        ...
        >>> show(host_labels_docker_container_status({}))
        cmk/docker_object:container
        >>> show(host_labels_docker_container_status({"ImageTags": []}))
        cmk/docker_object:container
        >>> show(host_labels_docker_container_status({"ImageTags": ["doctor:strange"]}))
        cmk/docker_object:container
        cmk/docker_image:doctor:strange
        cmk/docker_image_name:doctor
        cmk/docker_image_version:strange
        >>> show(host_labels_docker_container_status({"ImageTags": ["fiction/doctor:strange"]}))
        cmk/docker_object:container
        cmk/docker_image:fiction/doctor:strange
        cmk/docker_image_name:doctor
        cmk/docker_image_version:strange
        >>> show(host_labels_docker_container_status({"ImageTags": ["library:8080/fiction/doctor"]}))
        cmk/docker_object:container
        cmk/docker_image:library:8080/fiction/doctor
        cmk/docker_image_name:doctor

    """
    yield HostLabel("cmk/docker_object", "container")

    if isinstance(section, docker.MultipleNodesMarker):
        return

    image_tags = section.get("ImageTags")
    if not image_tags:
        return

    image = image_tags[-1]
    yield HostLabel("cmk/docker_image", "%s" % image)
    if "/" in image:
        __, image = image.rsplit("/", 1)
    if ":" in image:
        image_name, image_version = image.rsplit(":", 1)
        yield HostLabel("cmk/docker_image_name", "%s" % image_name)
        yield HostLabel("cmk/docker_image_version", "%s" % image_version)
    else:
        yield HostLabel("cmk/docker_image_name", "%s" % image)


agent_section_docker_container_status = AgentSection[Section](
    name="docker_container_status",
    parse_function=parse_docker_container_status,
    host_label_function=host_labels_docker_container_status,
)

# .
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


def discover_docker_container_status_health(section: Section) -> DiscoveryResult:
    if isinstance(section, docker.MultipleNodesMarker) or not _is_active_container(section):
        return
    # Only discover if a healthcheck and health is configured.
    # Stopped containers may have the 'Health' key anyway, so that's no criteria.
    # Blocked Healthcheck results in Health key not being present
    if {"Healthcheck", "Health"}.issubset(section):
        yield Service()


def check_docker_container_status_health(section: Section) -> CheckResult:
    if isinstance(section, docker.MultipleNodesMarker):
        return

    if section.get("Status") != "running":
        yield IgnoreResults("Container is not running")
        return

    health = section.get("Health", {})

    health_status = health.get("Status", "unknown")
    cur_state = HEALTH_STATUS_MAP.get(health_status, State.UNKNOWN)
    yield Result(state=cur_state, summary="Health status: %s" % health_status.title())

    last_log = (health.get("Log") or [{}])[-1]  # sometimes 'Log' value is an empty list
    # Remove "\n" from health_report string as this would currently raise a value error.
    # This was observed e.g. for the docker_container_status output of check-mk-enterprise:1.6.0p8
    health_report = last_log.get("Output", "no output").strip().replace("\n", ", ")
    if health_report:
        yield Result(
            state=State(int(last_log.get("ExitCode") != 0)),
            summary="Last health report: %s" % health_report,
        )

    if cur_state == State.CRIT:
        failing_streak = section.get("Health", {}).get("FailingStreak", "not found")
        yield Result(state=State.CRIT, summary="Failing streak: %s" % failing_streak)

    health_test = section.get("Healthcheck", {}).get("Test")
    if health_test:
        yield _health_test_result(f"Health test: {' '.join(health_test)}")


def _health_test_result(health_test: str) -> Result:
    """
    >>> _health_test_result("Health test: ./my_health_tests_script.sh")
    Result(state=<State.OK: 0>, summary='Health test: ./my_health_tests_script.sh')

    >>> r = _health_test_result("Health test: CMD-SHELL #!/bin/bash\\n\\nexit 0\\n")
    >>> r.summary
    'Health test: CMD-SHELL'
    >>> r.details
    'Health test: CMD-SHELL #!/bin/bash\\n\\nexit 0\\n'
    """
    return Result(
        state=State.OK,
        summary=health_test.split("\n", 1)[0].split("#!", 1)[0].strip(),
        details=health_test,
    )


check_plugin_docker_container_status_health = CheckPlugin(
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


def discover_docker_container_status(section: Section) -> DiscoveryResult:
    if isinstance(section, docker.MultipleNodesMarker) or _is_active_container(section):
        yield Service()


def check_docker_container_status(section: Section) -> CheckResult:
    if isinstance(section, docker.MultipleNodesMarker):
        yield Result(
            state=State.CRIT,
            summary="Found data from multiple Docker nodes - see service details for more information",
            details="This docker container apparently exists on multiple parent hosts. This should be "
            "reflected in the fact that this host has multiple piggyback sources, see the output of the "
            "Check_MK service. Hence, no definitive information on the container can be displayed. To "
            "resolve this situation, you have two options: 1. configure the docker agent plug-in to use "
            "the container IDs as host names, 2. use the ruleset 'Host name translation for piggybacked "
            "hosts' to create unique host names for the affected containers.",
        )
        return

    status = section.get("Status", "unknown")
    cur_state = {"running": State.OK, "unknown": State.UNKNOWN}.get(status, State.CRIT)

    # Please adjust PainterHostDockerNode if info is changed here
    # 5019 node = output.split()[-1]
    info = "Container %s" % status
    node_name = section.get("NodeName")
    if node_name:
        info += " on node %s" % node_name

    yield Result(state=cur_state, summary=info)

    if section.get("Error"):
        yield Result(state=State.CRIT, summary="Error: %s" % section["Error"])


check_plugin_docker_container_status = CheckPlugin(
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
# .


def discover_docker_container_status_uptime(
    section_docker_container_status: Section | None,
    section_uptime: uptime.Section | None,
) -> DiscoveryResult:
    if section_uptime:
        for _service in uptime.discover(section_uptime):
            # if the uptime service of the checkmk agent is
            # present, we don't need this service.
            return
    if not section_docker_container_status or isinstance(
        section_docker_container_status,
        docker.MultipleNodesMarker,
    ):
        return
    if (
        _is_active_container(section_docker_container_status)
        and "StartedAt" in section_docker_container_status
    ):
        yield Service()


def check_docker_container_status_uptime(
    params: Mapping[str, Any],
    section_docker_container_status: Section | None,
    section_uptime: uptime.Section | None,
) -> CheckResult:
    if not section_docker_container_status:
        return
    if isinstance(
        section_docker_container_status,
        docker.MultipleNodesMarker,
    ):
        return

    if not (started_str := section_docker_container_status.get("StartedAt")):
        return

    op_status = section_docker_container_status["Status"]
    if op_status == "running":
        utc_start = date_parser.parse(started_str)
        uptime_sec = (datetime.datetime.now(tz=datetime.UTC) - utc_start).total_seconds()
        yield from uptime.check(params, uptime.Section(int(uptime_sec), None))
    else:
        yield Result(state=State.OK, summary="Operational state: %s" % op_status)


check_plugin_docker_container_status_uptime = CheckPlugin(
    name="docker_container_status_uptime",
    sections=["docker_container_status", "uptime"],
    service_name="Uptime",
    discovery_function=discover_docker_container_status_uptime,
    check_ruleset_name="uptime",
    check_default_parameters={},
    check_function=check_docker_container_status_uptime,
)

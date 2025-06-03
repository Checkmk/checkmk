#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Agents

An agent is a small program that is installed on a host in order for Checkmk to be able query
data from the host.

An introduction to agents can be found in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_monitoringagents.html).

You can find more about the Agent Bakery and automatic agent updates of checkmk enterprise
in [Agent Deployment](https://docs.checkmk.com/latest/en/agent_deployment.html).
"""

from collections.abc import Mapping
from typing import Any

from cmk.gui.http import ContentDispositionType, Response
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.utils import agent

from cmk import fields

OS_TYPES_AVAILABLE_IN_RAW = ["linux_rpm", "linux_deb", "windows_msi"]

OS_TYPE_RAW = {
    "os_type": fields.String(
        description=(
            "The type of the operating system. May be one of "
            + ", ".join(OS_TYPES_AVAILABLE_IN_RAW)
        ),
        enum=sorted(OS_TYPES_AVAILABLE_IN_RAW),
        example="linux_deb",
        required=True,
    ),
}


@Endpoint(
    constructors.domain_type_action_href("agent", "download"),
    "cmk/download",
    method="get",
    content_type="application/octet-stream",
    query_params=[OS_TYPE_RAW],
)
def download_agent(params: Mapping[str, Any]) -> Response:
    """Download agents shipped with Checkmk"""
    os_type = params.get("os_type")
    response = Response()

    if os_type == "windows_msi":
        agent_path = agent.packed_agent_path_windows_msi()
        response.set_content_type("application/x-msi")
    elif os_type == "linux_rpm":
        agent_path = agent.packed_agent_path_linux_rpm()
        response.set_content_type("application/x-rpm")
    elif os_type == "linux_deb":
        agent_path = agent.packed_agent_path_linux_deb()
        response.set_content_type("application/x-deb")
    else:
        # This should never happen. Due to validation `os_type` can only be one
        # of the three elements above.
        raise AssertionError(f"Agent: os_type '{os_type}' not known in raw edition.")

    response.set_content_disposition(ContentDispositionType.ATTACHMENT, agent_path.name)

    with open(agent_path, mode="rb") as f:
        response.data = f.read()
    response.status_code = 200
    return response


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(download_agent, ignore_duplicates=ignore_duplicates)

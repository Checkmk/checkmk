#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Special agent: agent_gcp_status.

This agent retrieves the service status from https://status.cloud.google.com/incidents.json.
Since this feed is public, no authentication is required.
"""

import sys
import typing
from collections.abc import Sequence

import pydantic
import requests

from cmk.special_agents.v0_unstable import agent_common
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser


class DiscoveryParam(pydantic.BaseModel):
    """Config scheme: discovery for gcp_status.

    This is used by the discovery function of gcp_status. Configuration is passed in the special
    agent rule, so the user has a all-in-one view.
    """

    regions: list[str]


class AgentOutput(pydantic.BaseModel):
    """Section scheme: gcp_status

    Internal json, which is used to forward json between agent_gcp_status and the check.
    """

    discovery_param: DiscoveryParam
    # I do not want to make an explicit type for the incident schema
    # https://status.cloud.google.com/incidents.schema.json
    health_info: pydantic.Json


def _health_serializer(section: AgentOutput) -> None:
    with agent_common.SectionWriter("gcp_status") as w:
        w.append(section.model_dump_json())


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument(
        "regions",
        nargs="*",
        metavar="REGION1 REGION2",
        help="Regions, for which Checkmk services are discovered.",
    )
    return parser.parse_args(argv)


def _health_info() -> str:
    resp = requests.get("https://status.cloud.google.com/incidents.json", timeout=900)
    if resp.status_code == 200:
        return resp.text
    return "{}"


def write_section(args: Args, health_info: typing.Callable[[], str] = _health_info) -> int:
    response = health_info()
    section = AgentOutput(
        discovery_param=DiscoveryParam.model_validate(vars(args)),
        health_info=response,
    )
    _health_serializer(section)
    return 0


def main() -> int:
    return agent_common.special_agent_main(parse_arguments, write_section)


if __name__ == "__main__":
    sys.exit(main())

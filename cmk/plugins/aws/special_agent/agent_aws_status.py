#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Special agent: agent_aws_status.

This agent retrieves the rss feed from https://status.aws.amazon.com/rss/all.rss.
Since this feed is public, no authentication is required.
"""

import sys
import typing
from collections.abc import Sequence

import pydantic
import requests

from cmk.special_agents.v0_unstable import agent_common
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

Seconds = typing.NewType("Seconds", float)


class DiscoveryParam(pydantic.BaseModel):
    """Config scheme: discovery for aws_status.

    This configuration is not needed in the special agent, it is used by the discovery function of
    aws_status. Configuration is passed in the special agent rule, so the user has a all-in-one
    view.
    """

    regions: list[str]


class AgentOutput(pydantic.BaseModel):
    """Section scheme: aws_status

    Internal json, which is used to forward the rss feed between agent_aws_status and the check.
    """

    discovery_param: DiscoveryParam
    rss_str: str


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument(
        "regions",
        nargs="*",
        metavar="REGION1 REGION2",
        help="Regions, for which Checkmk services are discovered.",
    )
    return parser.parse_args(argv)


def _get_rss() -> requests.Response:
    return requests.get("https://status.aws.amazon.com/rss/all.rss", timeout=900)


def write_section(args: Args, get_rss: typing.Callable[[], requests.Response] = _get_rss) -> int:
    response = get_rss()
    section = AgentOutput(
        discovery_param=DiscoveryParam.model_validate(vars(args)),
        rss_str=response.text,
    )
    with agent_common.SectionWriter("aws_status") as writer:
        writer.append(section.model_dump_json())
    return 0


def main() -> int:
    return agent_common.special_agent_main(parse_arguments, write_section)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_gcp_status

This agent retrieves the service status from https://status.cloud.google.com/incidents.json.
Since this feed is public, no authentication is required.
"""

import argparse
import sys
import typing
from collections.abc import Sequence

import pydantic
import requests

from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

__version__ = "2.6.0b1"

AGENT = "gcp_status"


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
    health_info: pydantic.Json[object]


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(
        prog=prog, description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument(
        "--vcrtrace",
        "--tracefile",
        default=False,
        action=vcrtrace(
            # This is the result of a refactoring.
            # I did not check if it makes sense for this special agent.
            filter_headers=[("authorization", "****")],
        ),
    )
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


def write_section(
    args: argparse.Namespace, health_info: typing.Callable[[], str] = _health_info
) -> int:
    response = health_info()
    section = AgentOutput(
        discovery_param=DiscoveryParam.model_validate(vars(args)),
        health_info=response,
    )
    sys.stdout.write("<<<gcp_status:sep(0)>>>\n")
    sys.stdout.write(f"{section.model_dump_json()}\n")
    return 0


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    return write_section(parse_arguments(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())

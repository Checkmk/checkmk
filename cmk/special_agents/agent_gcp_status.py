#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Special agent: agent_gcp_status.

This agent retrieves the service status from https://status.cloud.google.com/incidents.json.
Since this feed is public, no authentication is required.
"""

import dataclasses
import sys
import typing
from collections.abc import Sequence

import requests

from cmk.special_agents.utils import agent_common
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser


@dataclasses.dataclass(frozen=True)
class HealthSection:
    # I do not want to make an explicit type for the incident schema
    # https://status.cloud.google.com/incidents.schema.json
    health_info: str

    def serialize(self) -> str:
        return self.health_info


def _health_serializer(section: HealthSection) -> None:
    with agent_common.SectionWriter("gcp_health") as w:
        w.append(section.serialize())


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    return parser.parse_args(argv)


def _health_info() -> str:
    resp = requests.get("https://status.cloud.google.com/incidents.json")
    if resp.status_code == 200:
        return resp.text
    return "{}"


def write_section(args: Args, health_info: typing.Callable[[], str] = _health_info) -> int:
    response = health_info()
    section = HealthSection(health_info=response)
    _health_serializer(section)
    return 0


def main() -> int:
    return agent_common.special_agent_main(parse_arguments, write_section)


if __name__ == "__main__":
    sys.exit(main())

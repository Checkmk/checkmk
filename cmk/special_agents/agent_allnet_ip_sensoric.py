#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This agent uses UPNP API calls to the Fritz!Box to gather information
# about connection configuration and status.
"""
Special Agent for Allnet IP-Sensoric monitoring
"""

import argparse
import re
import sys
from collections.abc import Mapping, Sequence

import requests

from cmk.special_agents.v0_unstable.agent_common import special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

_DEFAULT_TIMEOUT = 10


def parse_response_data(contents: str) -> Mapping[str, Mapping[str, str]]:
    parsed: dict[str, dict[str, str]] = {}
    context = None
    for line in contents.splitlines():
        match = re.search("<(sensor[0-9]+|system)>", line)
        if match:
            context = match.group(1)
            continue

        match = re.search("</(sensor[0-9]+|system)>", line)
        if match:
            context = None
            continue

        match = re.search(r"<(\w+)>(.+)</\w+>", line)
        if match and context:
            parsed.setdefault(context, {})[match.group(1)] = match.group(2)

    return parsed


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = create_default_argument_parser(__doc__)
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        metavar="SEC",
        default=_DEFAULT_TIMEOUT,
        help=(
            f"Set the network timeout to <SEC> seconds (default: {_DEFAULT_TIMEOUT}."
            "Note:"
            " The timeout is not applied to the whole check, it is used for the http query only."
        ),
    )
    parser.add_argument("host", help="Host name or IP address of your ALLNET IP-Sensoric")
    return parser.parse_args(argv if argv is not None else sys.argv[1:])


def _fetch_and_output_data(args: Args) -> int:
    url = f"http://{args.host}/xml/sensordata.xml"
    try:
        response = requests.get(
            url,
            headers={"User-agent": "Checkmk Special Agent Allnet IP Sensoric"},
            timeout=args.timeout,
        )
    except requests.ConnectionError:
        sys.stderr.write(f"Could not connect to host: {args.host}\n")
        return 1
    except requests.Timeout:
        sys.stderr.write("Connection timed out")
        return 1

    if response.status_code != 200:
        sys.stderr.write(f"{url}: {response.reason}")
        return 1

    sys.stdout.write("<<<allnet_ip_sensoric:sep(59)>>>\n")
    for sensor, readings in parse_response_data(response.text).items():
        for key, value in readings.items():
            sys.stdout.write(f"{sensor}.{key};{value}\n")

    return 0


def main() -> int:
    return special_agent_main(parse_arguments, _fetch_and_output_data)

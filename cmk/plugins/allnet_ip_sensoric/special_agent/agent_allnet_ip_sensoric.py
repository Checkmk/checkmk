#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_allnet_ip_sensoric

Checkmk special agent for monitoring Allnet IP-Sensoric devices.
"""

import argparse
import re
import sys
from collections.abc import Mapping, Sequence

import requests

from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

__version__ = "2.5.0b1"

AGENT = "allnet_ip_sensoric"

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
    return parser.parse_args(argv)


def _fetch_and_output_data(args: argparse.Namespace) -> int:
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


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    return _fetch_and_output_data(parse_arguments(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())

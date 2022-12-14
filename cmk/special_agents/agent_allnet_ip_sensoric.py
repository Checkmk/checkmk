#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This agent uses UPNP API calls to the Fritz!Box to gather information
# about connection configuration and status.
"""
Special Agent for Allnet IP-Sensoric monitoring
"""
import argparse
import pprint
import re
import socket
import sys
import traceback
from collections.abc import Sequence

import requests

from cmk.utils.exceptions import MKException

from cmk.special_agents.utils import vcrtrace

_DEFAULT_TIMEOUT = 10


class RequestError(MKException):
    pass


def get_allnet_ip_sensoric_info(host_address, opt_debug):
    contents = requests.get(
        f"http://{host_address}/xml/sensordata.xml",
        headers={"User-agent": "Checkmk Special Agent Allnet IP Sensoric"},
    ).text

    attrs = {}

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
            attrs[f"{context}.{match.group(1)}"] = match.group(2)

    if opt_debug:
        sys.stdout.write("Parsed: %s\n" % pprint.pformat(attrs))

    return attrs


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.formatter_class = argparse.RawTextHelpFormatter
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument("--vcrtrace", action=vcrtrace(filter_headers=[("authorization", "****")]))

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


def main(argv: Sequence[str] | None = None) -> None:

    if argv is None:
        argv = sys.argv[1:]
    args = parse_arguments(argv)

    socket.setdefaulttimeout(args.timeout)

    try:
        status = {}
        try:
            status.update(get_allnet_ip_sensoric_info(args.host, args.debug))
        except Exception:
            if args.debug:
                raise

        sys.stdout.write("<<<allnet_ip_sensoric:sep(59)>>>\n")
        for key, value in sorted(status.items()):
            sys.stdout.write(f"{key};{value}\n")

    except Exception:
        if args.debug:
            raise
        sys.stderr.write("Unhandled error: %s" % traceback.format_exc())

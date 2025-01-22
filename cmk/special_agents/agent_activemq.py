#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import xml.etree.ElementTree as ET
from collections.abc import Sequence

from requests.auth import HTTPBasicAuth

from cmk.special_agents.v0_unstable.agent_common import special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.v0_unstable.request_helper import ApiSession, parse_api_url


def parse_arguments(args: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument(
        "servername",
        type=str,
        metavar="SERVER",
        help="Name of the server",
    )
    parser.add_argument(
        "port",
        type=int,
        metavar="PORT_NUM",
        help="Port used for connecting to the server",
    )
    parser.add_argument(
        "--protocol",
        type=str,
        choices=["http", "https"],
        default="http",
        metavar="PROTOCOL",
        help="Protocol used for connecting to the server ('http' or 'https')",
    )
    parser.add_argument(
        "--piggyback",
        action="store_true",
        help="Activate piggyback mode",
    )
    parser.add_argument(
        "--username",
        type=str,
        metavar="USERNAME",
        help="Username for authenticating at the server",
    )
    parser.add_argument(
        "--password",
        type=str,
        metavar="PASSWORD",
        help="Password for authenticating at the server",
    )
    return parser.parse_args(args)


def agent_activemq_main(args: Args) -> int:
    api_url = parse_api_url(
        server_address=args.servername,
        api_path="admin/xml/",
        port=args.port,
        protocol=args.protocol,
    )

    auth = None
    if args.username:
        auth = HTTPBasicAuth(args.username, args.password)

    session = ApiSession(api_url, auth=auth)

    try:
        response = session.get("queues.jsp")
        if response.status_code == 401:
            raise Exception("Unauthorized")

        xml = response.text
        data = ET.fromstring(xml)
    except Exception as e:
        sys.stderr.write("Unable to connect. Credentials might be incorrect: %s\n" % e)
        return 1

    attributes = ["size", "consumerCount", "enqueueCount", "dequeueCount"]
    count = 0
    output_lines = []
    try:
        if not args.piggyback:
            output_lines.append("<<<mq_queues>>>")

        for line in data:
            count += 1
            if args.piggyback:
                output_lines.append("<<<<%s>>>>" % line.get("name"))
                output_lines.append("<<<mq_queues>>>")
            output_lines.append("[[%s]]" % line.get("name"))
            stats = line.findall("stats")
            values = ""
            for job in attributes:
                values += "%s " % stats[0].get(job)
            output_lines.append(values)

        if args.piggyback:
            output_lines.append("<<<<>>>>")
            output_lines.append("<<<local:sep(0)>>>")
            output_lines.append("0 Active_MQ - Found %s Queues in total" % count)
    except Exception as e:  # Probably an IndexError
        sys.stderr.write("Unable to process data. Returned data might be incorrect: %r" % e)
        return 1

    sys.stdout.write("\n".join(output_lines) + "\n")
    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(
        parse_arguments,
        agent_activemq_main,
    )

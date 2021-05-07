#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import getopt
import sys
import xml.etree.ElementTree as ET
from typing import Optional, Sequence

from requests.auth import HTTPBasicAuth

from cmk.special_agents.utils.agent_common import special_agent_main
from cmk.special_agents.utils.argument_parsing import Args
from cmk.special_agents.utils.request_helper import create_api_connect_session, parse_api_url


def usage():
    print("Usage:")
    print(
        "agent_activemq --servername {servername} --port {port} [--piggyback] [--username {username} --password {password}] [--protocol {http|https}]\n"
    )


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    short_options = ""
    long_options = ["piggyback", "servername=", "port=", "username=", "password=", "protocol="]

    try:
        opts, _args = getopt.getopt(
            list(argv) if argv else [],
            short_options,
            long_options,
        )
    except getopt.GetoptError as err:
        usage()
        sys.stderr.write("%s\n" % err)
        sys.exit(2)

    args = Args(
        servername=None,
        port=None,
        username=None,
        password=None,
        piggyback=False,
        protocol="http",
        verbose=False,
    )

    for o, a in opts:
        if o in ['--piggyback']:
            args.piggyback = True
        elif o in ['--servername']:
            args.servername = a
        elif o in ['--port']:
            args.port = a
        elif o in ['--username']:
            args.username = a
        elif o in ['--password']:
            args.password = a
        elif o in ['--protocol']:
            args.protocol = a

    if not args.servername or not args.port:
        usage()
        sys.exit(2)

    return args


def agent_activemq_main(args: Args) -> None:
    api_url = parse_api_url(
        server_address=args.servername,
        api_path="/admin/xml/",
        port=args.port,
        protocol=args.protocol,
    )

    auth = None
    if args.username:
        auth = HTTPBasicAuth(args.username, args.password)

    session = create_api_connect_session(api_url, auth=auth)

    try:
        response = session.get("queues.jsp")
        if response.status_code == 401:
            raise Exception("Unauthorized")

        xml = response.text
        data = ET.fromstring(xml)
    except Exception as e:
        sys.stderr.write("Unable to connect. Credentials might be incorrect: %s\n" % e)
        return

    attributes = ['size', 'consumerCount', 'enqueueCount', 'dequeueCount']
    count = 0
    output_lines = []
    try:
        if not args.piggyback:
            output_lines.append("<<<mq_queues>>>")

        for line in data:
            count += 1
            if args.piggyback:
                output_lines.append("<<<<%s>>>>" % line.get('name'))
                output_lines.append("<<<mq_queues>>>")
            output_lines.append("[[%s]]" % line.get('name'))
            stats = line.findall('stats')
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
        return

    print("\n".join(output_lines))


def main() -> None:
    """Main entry point to be used """
    special_agent_main(
        parse_arguments,
        agent_activemq_main,
    )

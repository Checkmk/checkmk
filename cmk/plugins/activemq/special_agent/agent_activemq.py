#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_activemq

Checkmk special agent for monitoring ActiveMQ servers.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from typing import Literal
from urllib.parse import urljoin

from requests import Response, Session
from requests.auth import HTTPBasicAuth

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import (
    HostnameValidationAdapter,
    report_agent_crashes,
    vcrtrace,
)

__version__ = "2.6.0b1"

AGENT = "activemq"

PASSWORD_OPTION = "password"


def parse_arguments(args: Sequence[str] | None) -> argparse.Namespace:
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
    parser_add_secret_option(
        parser,
        long=f"--{PASSWORD_OPTION}",
        required=False,
        help="Password for authenticating at the server",
    )
    return parser.parse_args(args)


class ApiSession:
    """Class for issuing multiple API calls

    ApiSession behaves similar to requests.Session with the exception that a
    base URL is provided and persisted.
    All requests use the base URL and append the provided url to it.
    """

    def __init__(
        self,
        base_url: str,
        auth: HTTPBasicAuth | None = None,
        tls_cert_verification: bool | HostnameValidationAdapter = True,
        additional_headers: Mapping[str, str] | None = None,
    ):
        self._session = Session()
        self._session.auth = auth
        self._session.headers.update(additional_headers or {})
        self._base_url = base_url

        if isinstance(tls_cert_verification, HostnameValidationAdapter):
            self._session.mount(self._base_url, tls_cert_verification)
            self.verify = True
        else:
            self.verify = tls_cert_verification

    def request(
        self,
        method: str,
        url: str,
        params: Mapping[str, str] | None = None,
    ) -> Response:
        return self._session.request(
            method,
            urljoin(self._base_url, url),
            params=params,
            verify=self.verify,
        )

    def get(
        self,
        url: str,
        params: Mapping[str, str] | None = None,
    ) -> Response:
        return self.request(
            "get",
            url,
            params=params,
        )


def _parse_api_url(
    server_address: str,
    protocol: Literal["http", "https"],
    port: int | None,
) -> str:
    address_start = f"{protocol}://{server_address}"
    if port:
        address = f"{address_start}:{port}"
    else:
        address = f"{address_start}"

    return f"{address}/admin/xml/"


def agent_activemq_main(args: argparse.Namespace) -> int:
    api_url = _parse_api_url(
        server_address=args.servername,
        port=args.port,
        protocol=args.protocol,
    )

    auth = None
    if args.username:
        auth = HTTPBasicAuth(args.username, resolve_secret_option(args, PASSWORD_OPTION).reveal())

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


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    """Main entry point to be used"""
    return agent_activemq_main(parse_arguments(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())

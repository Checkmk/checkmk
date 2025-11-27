#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_hivemanager

Checkmk special agent for monitoring Hivemanager devices.
"""

import argparse
import base64
import json
import sys
from collections.abc import Sequence

import requests

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import HostnameValidationAdapter, report_agent_crashes

__version__ = "2.5.0b1"

AGENT = "hivemanager"

PASSWORD_OPTION = "password"


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    return _main(parse_arguments(sys.argv[1:]))


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "server",
        help="Hivemanager server address",
    )
    parser.add_argument("--user", help="Hivemanager API username", required=True)
    parser_add_secret_option(
        parser,
        long=f"--{PASSWORD_OPTION}",
        help="Hivemanager API password",
        required=True,
    )
    parser.add_argument(
        "--cert-server-name",
        metavar="CERT-SERVER-NAME",
        help="Use this server name for TLS certificate validation",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Be more verbose",
    )
    return parser.parse_args(argv)


def _main(args: argparse.Namespace) -> int:
    session = _session(
        server=args.server,
        username=args.user,
        password=resolve_secret_option(args, PASSWORD_OPTION).reveal(),
        cert_server_name=args.cert_server_name,
    )

    try:
        data = session.get(
            f"https://{args.server}/hm/api/v1/devices",
            timeout=900,
        ).text
    except Exception as e:
        sys.stderr.write("Connection error: %s" % e)
        return 2

    informations = [
        "hostName",
        "clients",
        "alarm",
        "connection",
        "upTime",
        "eth0LLDPPort",
        "eth0LLDPSysName",
        "hive",
        "hiveOS",
        "hwmodel",
        "serialNumber",
        "nodeId",
        "location",
        "networkPolicy",
    ]

    sys.stdout.write("<<<hivemanager_devices:sep(124)>>>\n")
    for line in json.loads(data):
        if line["upTime"] == "":
            line["upTime"] = "down"
        sys.stdout.write(
            "|".join(map(str, [f"{x}::{y}" for x, y in line.items() if x in informations])) + "\n"
        )
    return 0


def _session(
    *,
    server: str,
    username: str,
    password: str,
    cert_server_name: str | None,
) -> requests.Session:
    session = requests.session()
    session.headers.update(
        {
            "Authorization": "Basic %s"
            % (
                base64.encodebytes(f"{username}:{password}".encode())
                .decode("utf-8")
                .replace("\n", "")
            ),
            "Content-Type": "application/json",
        }
    )
    if cert_server_name:
        session.mount(
            f"https://{server}",
            HostnameValidationAdapter(cert_server_name),
        )
    return session

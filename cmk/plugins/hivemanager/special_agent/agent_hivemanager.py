#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import base64
import json
import sys
from collections.abc import Sequence

import requests

from cmk.special_agents.v0_unstable.agent_common import special_agent_main
from cmk.special_agents.v0_unstable.request_helper import HostnameValidationAdapter


def main() -> int:
    return special_agent_main(_parse_arguments, _main)


def _parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "server",
        help="Hivemanager server address",
    )
    parser.add_argument(
        "user",
        help="Hivemanager API username",
    )
    parser.add_argument(
        "password",
        help="Hivemanager API password",
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
        password=args.password,
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

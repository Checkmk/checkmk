#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
import socket
import sys
from collections.abc import Sequence
from dataclasses import dataclass

import requests

from cmk.utils.password_store import replace_passwords

from cmk.special_agents.v0_unstable.request_helper import HostnameValidationAdapter


# TODO: put into special_agent lib
def get_agent_info_tcp(host: str) -> bytes:
    ipaddress = socket.gethostbyname(host)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect((ipaddress, 6556))

    try:
        s.setblocking(True)
    except Exception:
        pass

    resp = b""
    while True:
        out = s.recv(4096, socket.MSG_WAITALL)
        if out and len(out) > 0:
            resp += out
        else:
            break
    s.close()
    return resp


def main() -> int:
    replace_passwords()
    sys_argv = sys.argv[1:]

    args = _parse_arguments(sys_argv)

    try:
        base_url = f"http://{args.address}/api/v1/venues/{args.venueid}"

        endpoints = [
            ("access_points/statuses.json", "ap"),
            ("locations/last_known.json", "locations"),
        ]
        with requests.Session() as session:
            if args.cert_server_name is not None:
                session.mount(base_url, HostnameValidationAdapter(args.cert_server_name))

            for url_end, section_type in endpoints:
                _fetch_data_and_write_to_stdout(
                    session, f"{base_url}/{url_end}", args.apikey, section_type
                )

        if args.agent_port is not None:
            hostname = args.address.split(":")[0]
            sys.stdout.write(get_agent_info_tcp(hostname).decode())

    except Exception as e:
        sys.stderr.write("Connection error %s" % e)
        return 1
    return 0


@dataclass(frozen=True, kw_only=True)
class _Arguments:
    address: str
    venueid: str
    apikey: str
    agent_port: int | None = None
    cert_server_name: str | None = None


def _parse_arguments(argv: Sequence[str]) -> _Arguments:
    parser = argparse.ArgumentParser(description="Check_MK Ruckus Spot Agent")

    parser.add_argument(
        "address",
        help="Address {hostname:port}",
    )
    parser.add_argument(
        "venueid",
        help="Venue ID",
    )
    parser.add_argument(
        "apikey",
        help="API key",
    )
    parser.add_argument(
        "--agent_port",
        type=int,
        help="Agent port",
    )
    parser.add_argument(
        "--cert-server-name",
        help="Use this server name for TLS certificate validation.",
    )
    args = parser.parse_args(argv)

    return _Arguments(
        address=args.address,
        venueid=args.venueid,
        apikey=args.apikey,
        agent_port=args.agent_port,
        cert_server_name=args.cert_server_name,
    )


def _fetch_data_and_write_to_stdout(
    session: requests.Session,
    url: str,
    apikey: str,
    section_type: str,
) -> None:
    response = session.get(url, auth=(apikey, "X"), timeout=900)
    sys.stdout.write(f"<<<ruckus_spot_{section_type}:sep(0)>>>\n")
    sys.stdout.write(response.text + "\n")

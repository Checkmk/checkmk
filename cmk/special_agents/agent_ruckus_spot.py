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
        for url_end, section_type in [
            ("access_points/statuses.json", "ap"),
            ("locations/last_known.json", "locations"),
        ]:
            url = f"http://{args.address}/api/v1/venues/{args.venueid}/{url_end}"
            response = requests.get(url, auth=(args.apikey, "X"))  # nosec B113 # BNS:0b0eac

            sys.stdout.write("<<<ruckus_spot_%s:sep(0)>>>\n" % section_type)
            sys.stdout.write(response.text + "\n")

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
    args = parser.parse_args(argv)

    return _Arguments(
        address=args.address,
        venueid=args.venueid,
        apikey=args.apikey,
        agent_port=args.agent_port,
    )

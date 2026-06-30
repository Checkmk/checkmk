#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_hivemanager_ng

Checkmk special agent for Aerohive HiveManager NG."""

import sys
import traceback
from argparse import ArgumentParser
from argparse import Namespace as Args
from collections.abc import Mapping, Sequence
from typing import NoReturn

import requests

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option

SECRET_OPTION = "secret"

# The agent delivers at most this many devices.
_PAGE_SIZE = 1000

# Device field names forwarded to the check plugin; all other fields are dropped.
_USED_FIELDS = {
    "hostName",
    "connected",
    "activeClients",
    "ip",
    "serialId",
    "osVersion",
    "lastUpdated",
}


def bail_out(message: str, debug: bool = False) -> NoReturn:
    if debug:
        sys.stderr.write("----------------------------------\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("==================================\n")
    sys.stderr.write("Error: %s\n" % message)
    sys.exit(1)


def parse_arguments(argv: Sequence[str]) -> Args:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = ArgumentParser(description=description, prog=prog)
    parser.add_argument("-d", "--debug", help="enable debugging", action="store_true")
    parser.add_argument("url", help="URL to Aerohive NG, e.g. https://cloud.aerohive.com")
    parser.add_argument("vhm_id", help="Numericl ID of the VHM e.g. 102")
    parser.add_argument("api_token", help="API Access Token")
    parser.add_argument("client_id", help="Client ID")
    parser_add_secret_option(parser, long=f"--{SECRET_OPTION}", help="Client secret", required=True)
    parser.add_argument("redirect_url", help="Redirect URL")
    return parser.parse_args(argv)


def device_line(device: Mapping[str, object]) -> str:
    """Render a single device as a section line, keeping only the used fields."""
    return "|".join(f"{key}::{value}" for key, value in device.items() if key in _USED_FIELDS)


def fetch_devices(args: Args) -> Sequence[Mapping[str, object]]:
    """Query the HiveManager NG API and return the list of devices."""
    params = {
        "ownerId": args.vhm_id,
        "pageSize": _PAGE_SIZE,
    }
    headers = {
        "Authorization": "Bearer %s" % args.api_token,
        "X-AH-API-CLIENT-ID": args.client_id,
        "X-AH-API-CLIENT-SECRET": resolve_secret_option(args, SECRET_OPTION).reveal(),
        "X-AH-API-CLIENT-REDIRECT-URI": args.redirect_url,
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(
            "%s/xapi/v1/monitor/devices" % args.url,
            headers=headers,
            params=params,
            timeout=900,
        )
    except requests.RequestException:
        bail_out(
            "Request to the API failed. Please check your connection settings. "
            "A guide to setup the API can be found on the Aerohive homepage.",
            args.debug,
        )

    try:
        json = response.json()
    except ValueError as e:
        bail_out(e.args[0], args.debug)

    if json["error"]:
        bail_out(
            "Error in JSON response. Please check your connection settings. "
            "A guide to setup the API can be found on the Aerohive "
            "homepage.",
            args.debug,
        )

    devices: Sequence[Mapping[str, object]] = json["data"]
    return devices


def main() -> int:
    args = parse_arguments(sys.argv[1:])

    sys.stdout.write("<<<hivemanager_ng_devices:sep(124)>>>\n")

    for device in fetch_devices(args):
        sys.stdout.write(device_line(device) + "\n")

    return 0


if __name__ == "__main__":
    main()

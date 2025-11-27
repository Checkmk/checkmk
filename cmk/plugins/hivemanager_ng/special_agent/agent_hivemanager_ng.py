#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_hivemanager_ng

Checkmk special agent for Aerohive HiveManagerNG.
"""

import argparse
import sys
import traceback
from collections.abc import Sequence
from typing import NoReturn

import requests

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option

SECRET_OPTION = "secret"


def bail_out(message: str, debug: bool = False) -> NoReturn:
    if debug:
        sys.stderr.write("----------------------------------\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("==================================\n")
    sys.stderr.write("Error: %s\n" % message)
    sys.exit(1)


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(description=description, prog=prog)
    parser.add_argument("-d", "--debug", help="enable debugging", action="store_true")
    parser.add_argument("url", help="URL to Aerohive NG, e.g. https://cloud.aerohive.com")
    parser.add_argument("vhm_id", help="Numericl ID of the VHM e.g. 102")
    parser.add_argument("api_token", help="API Access Token")
    parser.add_argument("client_id", help="Client ID")
    parser_add_secret_option(parser, long=f"--{SECRET_OPTION}", help="Client secret", required=True)
    parser.add_argument("redirect_url", help="Redirect URL")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_arguments(sys.argv[1:])

    sys.stdout.write("<<<hivemanager_ng_devices:sep(124)>>>\n")

    address = "%s/xapi/v1/monitor/devices" % args.url
    params = {
        "ownerId": args.vhm_id,
        "pageSize": 1000,  # the agent will deliver at most 1000 devices
    }
    headers = {
        "Authorization": "Bearer %s" % args.api_token,
        "X-AH-API-CLIENT-ID": args.client_id,
        "X-AH-API-CLIENT-SECRET": resolve_secret_option(args, SECRET_OPTION).reveal(),
        "X-AH-API-CLIENT-REDIRECT-URI": args.redirect_url,
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(address, headers=headers, params=params, timeout=900)
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

    used = {
        "hostName",
        "connected",
        "activeClients",
        "ip",
        "serialId",
        "osVersion",
        "lastUpdated",
    }

    for device in json["data"]:
        device_txt = "|".join([f"{k}::{v}" for (k, v) in device.items() if k in used])
        sys.stdout.write(device_txt + "\n")

    return 0


if __name__ == "__main__":
    main()

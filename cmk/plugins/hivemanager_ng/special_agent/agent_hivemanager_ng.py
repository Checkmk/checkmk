#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_hivemanager_ng

Checkmk special agent for Extreme Networks ExtremeCloud IQ (formerly Aerohive HiveManager NG).
"""

import sys
import traceback
from argparse import ArgumentParser
from argparse import Namespace as Args
from collections.abc import Mapping, Sequence
from typing import NoReturn

import requests

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option

SECRET_OPTION = "password"

# Number of devices to request per page of the device list. Must be <= 100.
_PAGE_SIZE = 100

# Seconds to wait for the API to respond.
_REQUEST_TIMEOUT = 900

# Mapping of the section field names the check plugin expects to the field names
# returned by the ExtremeCloud IQ "GET /devices" endpoint.
_DEVICE_FIELDS = {
    "hostName": "hostname",
    "connected": "connected",
    "activeClients": "active_clients",
    "ip": "ip_address",
    "serialId": "serial_number",
    "osVersion": "software_version",
    "lastUpdated": "last_connect_time",
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
    parser.add_argument(
        "url",
        help="Base URL of the ExtremeCloud IQ API, e.g. https://api.extremecloudiq.com",
    )
    parser.add_argument("username", help="ExtremeCloud IQ username")
    parser_add_secret_option(parser, long=f"--{SECRET_OPTION}", help="Client secret", required=True)
    return parser.parse_args(argv)


def device_line(device: Mapping[str, object]) -> str:
    """Render a single device as a section line in the legacy field format."""
    values = {section_key: device.get(api_key) for section_key, api_key in _DEVICE_FIELDS.items()}
    # The check plugin expects a boolean-like string and an integer for these fields.
    values["connected"] = bool(values["connected"])
    active_clients = values["activeClients"]
    values["activeClients"] = int(active_clients) if isinstance(active_clients, int | str) else 0
    return "|".join(f"{key}::{value}" for key, value in values.items())


def login(base_url: str, username: str, password: str) -> str:
    """Authenticate and return the JWT bearer token for subsequent requests."""
    response = requests.post(
        f"{base_url}/login",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"username": username, "password": password},
        timeout=_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    access_token: str = response.json()["access_token"]
    return access_token


def logout(base_url: str, headers: Mapping[str, str]) -> None:
    requests.post(f"{base_url}/logout", headers=headers, timeout=_REQUEST_TIMEOUT)


def fetch_devices(base_url: str, headers: Mapping[str, str]) -> Sequence[Mapping[str, object]]:
    """Retrieve all devices, following the API's pagination until the last page."""
    devices: list[Mapping[str, object]] = []
    page = 1
    while True:
        response = requests.get(
            f"{base_url}/devices",
            headers=headers,
            params={
                "views": "FULL",  # include operational data such as the active client count
                "page": str(page),
                "limit": str(_PAGE_SIZE),
            },
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        devices += payload["data"]
        if page >= payload["total_pages"]:
            return devices
        page += 1


def main() -> int:
    args = parse_arguments(sys.argv[1:])
    base_url = args.url.rstrip("/")

    sys.stdout.write("<<<hivemanager_ng_devices:sep(124)>>>\n")
    try:
        try:
            jwt_token = login(
                base_url, args.username, resolve_secret_option(args, SECRET_OPTION).reveal()
            )
            auth_headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            devices = fetch_devices(base_url, auth_headers)
        except (ValueError, KeyError, TypeError) as exc:
            bail_out("Unexpected response from the ExtremeCloud IQ API: %s" % exc, args.debug)
        logout(base_url, auth_headers)
    except requests.RequestException:
        bail_out(
            "Request to the ExtremeCloud IQ API failed. Please check your connection settings "
            "and your credentials.",
            args.debug,
        )

    for device in devices:
        sys.stdout.write(device_line(device) + "\n")

    return 0


if __name__ == "__main__":
    main()

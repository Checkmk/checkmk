#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_extremecloud_iq

Checkmk special agent for Extreme Networks ExtremeCloud IQ (formerly Aerohive HiveManager NG).
"""

import itertools
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager

import requests

from cmk.password_store.v1_unstable import (
    parser_add_secret_option,
    resolve_secret_option,
    Secret,
)
from cmk.server_side_programs.v1_unstable import report_agent_crashes

__version__ = "2.5.0p14"

AGENT = "extremecloud_iq"

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


def parse_arguments(argv: Sequence[str]) -> Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = ArgumentParser(description=description, prog=prog)
    parser.add_argument("-d", "--debug", action="store_true", help="enable debugging")
    parser.add_argument(
        "url",
        help="Base URL of the ExtremeCloud IQ API, e.g. https://api.extremecloudiq.com",
    )
    parser.add_argument("username", help="ExtremeCloud IQ username")
    parser_add_secret_option(
        parser, long=f"--{SECRET_OPTION}", help="ExtremeCloud IQ password", required=True
    )
    return parser.parse_args(argv)


def device_line(device: Mapping[str, object]) -> str:
    """Render a single device as a section line in the legacy field format."""
    values = {section_key: device.get(api_key) for section_key, api_key in _DEVICE_FIELDS.items()}
    # The check plugin expects a boolean-like string and an integer for these fields.
    values["connected"] = bool(values["connected"])
    active_clients = values["activeClients"]
    values["activeClients"] = int(active_clients) if isinstance(active_clients, int | str) else 0
    return "|".join(f"{key}::{value}" for key, value in values.items())


def login(base_url: str, username: str, secret: Secret[str]) -> str:
    """Authenticate and return the JWT bearer token for subsequent requests."""
    response = requests.post(
        f"{base_url}/login",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"username": username, "password": secret.reveal()},
        timeout=_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    access_token: str = response.json()["access_token"]
    return access_token


def logout(base_url: str, headers: Mapping[str, str]) -> None:
    requests.post(f"{base_url}/logout", headers=headers, timeout=_REQUEST_TIMEOUT)


@contextmanager
def logged_in(base_url: str, username: str, secret: Secret[str]) -> Iterator[Mapping[str, str]]:
    """Log in, yield the authorization headers and release the token again on exit."""
    token = login(base_url, username, secret)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        yield headers
    finally:
        logout(base_url, headers)


def fetch_devices(base_url: str, headers: Mapping[str, str]) -> Sequence[Mapping[str, object]]:
    """Retrieve all devices, following the API's pagination until the last page."""
    devices: list[Mapping[str, object]] = []
    for page in itertools.count(start=1):
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
    raise AssertionError("unreachable but ruff will scream RET503")


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    return _main(parse_arguments(sys.argv[1:]))


def _main(args: Namespace) -> int:
    base_url = args.url.rstrip("/")
    try:
        with logged_in(
            base_url,
            args.username,
            resolve_secret_option(args, SECRET_OPTION),
        ) as auth_headers:
            devices = fetch_devices(base_url, auth_headers)
    except requests.RequestException:
        sys.stderr.write(
            "Error: Communication with the ExtremeCloud IQ API failed. "
            "Please check the URL, username and password.\n"
        )
        return 1

    # Section name is legacy and kept for compatibility reasons
    sys.stdout.write("<<<hivemanager_ng_devices:sep(124)>>>\n")
    for device in devices:
        sys.stdout.write(device_line(device) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

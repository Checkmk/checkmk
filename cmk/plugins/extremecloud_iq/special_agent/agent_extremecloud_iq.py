#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_extremecloud_iq

Checkmk special agent for Extreme Networks ExtremeCloud IQ (formerly Aerohive HiveManager NG).
"""

import itertools
import pathlib
import sys
from argparse import Namespace
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager

import requests

from cmk.utils import password_store

from cmk.special_agents.v0_unstable.agent_common import special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import create_default_argument_parser

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


def parse_arguments(argv: Sequence[str] | None) -> Namespace:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument(
        "url",
        help="Base URL of the ExtremeCloud IQ API, e.g. https://api.extremecloudiq.com",
    )
    parser.add_argument("username", help="ExtremeCloud IQ username")
    group_password = parser.add_mutually_exclusive_group(required=True)
    group_password.add_argument(
        "--password-ref",
        help="Password store reference to the ExtremeCloud IQ password.",
    )
    group_password.add_argument("--password", help="ExtremeCloud IQ password")
    return parser.parse_args(argv)


def get_password_from_args(args: Namespace) -> str:
    if args.password:
        return args.password

    pw_id, pw_file = args.password_ref.split(":", maxsplit=1)

    return password_store.lookup(pathlib.Path(pw_file), pw_id)


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


@contextmanager
def logged_in(base_url: str, username: str, password: str) -> Iterator[Mapping[str, str]]:
    """Log in, yield the authorization headers and release the token again on exit."""
    token = login(base_url, username, password)
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


def main() -> int:
    return special_agent_main(parse_arguments, _main)


def _main(args: Namespace) -> int:
    base_url = args.url.rstrip("/")
    try:
        with logged_in(
            base_url,
            args.username,
            get_password_from_args(args),
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

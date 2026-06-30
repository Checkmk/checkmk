#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk special agent for Extreme Networks ExtremeCloud IQ (formerly Aerohive HiveManager NG)."""

import argparse
import sys
import traceback

import requests

from cmk.utils.password_store import replace_passwords

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


def bail_out(message, debug=False):
    if debug:
        sys.stderr.write("----------------------------------\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("==================================\n")
    sys.stderr.write("Error: %s\n" % message)
    sys.exit(1)


class ArgParser(argparse.ArgumentParser):
    # Use custom behaviour on error
    def error(self, message):
        bail_out("Parsing the arguments failed - %s." % message)


def parse_arguments(argv):
    parser = ArgParser(
        description="Special agent to retrieve data from Extreme Networks ExtremeCloud IQ"
    )
    parser.add_argument("-d", "--debug", help="enable debugging", action="store_true")
    parser.add_argument(
        "url",
        help="Base URL of the ExtremeCloud IQ API, e.g. https://api.extremecloudiq.com",
    )
    parser.add_argument("username", help="ExtremeCloud IQ username")
    parser.add_argument("password", help="ExtremeCloud IQ password")
    return parser.parse_args(argv)


def device_line(device):
    """Render a single device as a section line in the legacy field format."""
    values = {section_key: device.get(api_key) for section_key, api_key in _DEVICE_FIELDS.items()}
    # The check plugin expects a boolean-like string and an integer for these fields.
    values["connected"] = bool(values["connected"])
    values["activeClients"] = int(values["activeClients"] or 0)
    return "|".join(f"{key}::{value}" for key, value in values.items())


def login(base_url, username, password):
    """Authenticate and return the JWT bearer token for subsequent requests."""
    response = requests.post(
        f"{base_url}/login",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"username": username, "password": password},
        timeout=_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def logout(base_url, headers):
    requests.post(f"{base_url}/logout", headers=headers, timeout=_REQUEST_TIMEOUT)


def fetch_devices(base_url, headers):
    """Retrieve all devices, following the API's pagination until the last page."""
    devices = []
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


def main():
    replace_passwords()
    args = parse_arguments(sys.argv[1:])
    base_url = args.url.rstrip("/")

    sys.stdout.write("<<<hivemanager_ng_devices:sep(124)>>>\n")
    try:
        try:
            jwt_token = login(base_url, args.username, args.password)
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

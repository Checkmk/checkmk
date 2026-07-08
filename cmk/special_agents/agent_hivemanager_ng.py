#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk special agent for Aerohive HiveManager NG."""

import argparse
import sys
import traceback

import requests

from cmk.utils.password_store import replace_passwords

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
    parser = ArgParser(description="Special agent to retrieve data from Aerohive HiveManagerNG")
    parser.add_argument("-d", "--debug", help="enable debugging", action="store_true")
    parser.add_argument("url", help="URL to Aerohive NG, e.g. https://cloud.aerohive.com")
    parser.add_argument("vhm_id", help="Numericl ID of the VHM e.g. 102")
    parser.add_argument("api_token", help="API Access Token")
    parser.add_argument("client_id", help="Client ID")
    parser.add_argument("client_secret", help="Client secret")
    parser.add_argument("redirect_url", help="Redirect URL")
    return parser.parse_args(argv)


def device_line(device):
    """Render a single device as a section line, keeping only the used fields."""
    return "|".join(f"{key}::{value}" for key, value in device.items() if key in _USED_FIELDS)


def fetch_devices(args):
    """Query the HiveManager NG API and return the list of devices."""
    params = {
        "ownerId": args.vhm_id,
        "pageSize": _PAGE_SIZE,
    }
    headers = {
        "Authorization": "Bearer %s" % args.api_token,
        "X-AH-API-CLIENT-ID": args.client_id,
        "X-AH-API-CLIENT-SECRET": args.client_secret,
        "X-AH-API-CLIENT-REDIRECT-URI": args.redirect_url,
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(
            "%s/xapi/v1/monitor/devices" % args.url,
            headers=headers,
            params=params,
        )  # nosec B113 # BNS:0b0eac
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

    return json["data"]


def main():
    replace_passwords()
    args = parse_arguments(sys.argv[1:])

    sys.stdout.write("<<<hivemanager_ng_devices:sep(124)>>>\n")

    for device in fetch_devices(args):
        sys.stdout.write(device_line(device) + "\n")

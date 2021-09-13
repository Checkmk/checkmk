#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Common module for stuff every special agent should use
Current responsibilities include:
* vcrtrace
* manages password store
* agent output handling
* common argument parsing
* logging
"""

import argparse
from typing import Optional

from cmk.special_agents.utils import vcrtrace  # pylint: disable=cmk-module-layer-violation

Args = argparse.Namespace


def create_default_argument_parser(description: Optional[str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.formatter_class = argparse.RawTextHelpFormatter
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument(
        "--vcrtrace", "--tracefile", action=vcrtrace(filter_headers=[("authorization", "****")])
    )
    return parser


def parse_connection_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Parse the connection command line arguments"""
    parser.add_argument(
        "--address", dest="address", help="address of the connection", metavar="ADDRESS"
    )
    parser.add_argument(
        "--port", dest="port", type=int, help="port of the connection", metavar="PORT"
    )
    parser.add_argument("--protocol", dest="protocol", help="the protocol type", metavar="PROTOCOL")
    parser.add_argument(
        "--username", dest="username", help="the username for authentication", metavar="USERNAME"
    )
    parser.add_argument(
        "--password", dest="password", help="the password for authentication", metavar="PASSWORD"
    )
    parser.add_argument(
        "--token", dest="token", help="the API token for authentication", metavar="TOKEN"
    )
    parser.add_argument(
        "--no-cert-check",
        dest="no_cert_check",
        help="if SSL certificate should be verified",
        metavar="SSL",
    )
    parser.add_argument(
        "--url-custom",
        dest="url_custom",
        help="a custom URL to connect to the server",
        metavar="CUSTOM",
    )

    return parser

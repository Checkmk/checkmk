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

from typing import Optional
import argparse
from cmk.special_agents.utils import vcrtrace  # pylint: disable=cmk-module-layer-violation

Args = argparse.Namespace


def create_default_argument_parser(description: Optional[str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.formatter_class = argparse.RawTextHelpFormatter
    parser.add_argument("--debug",
                        "-d",
                        action="store_true",
                        help="Enable debug mode (keep some exceptions unhandled)")
    parser.add_argument("--verbose", '-v', action="count", default=0)
    parser.add_argument("--vcrtrace",
                        "--tracefile",
                        action=vcrtrace(filter_headers=[('authorization', '****')]))
    return parser

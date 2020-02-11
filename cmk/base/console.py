#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Utiliy module for holding generic methods that implement handling
of console input / output"""

import logging
import sys
from typing import Any, IO, Text  # pylint: disable=unused-import

from cmk.utils.log import VERBOSE
import cmk.utils.tty as tty

# NOTE: This is a hack! We abuse the global logger just to pass around the
# verbosity setting.
logger = logging.getLogger("cmk.base")

#
# Generic / low level functions
#


# would rather use "def output(text, *args, stream=sys.stdout)", but this is not possible
# with python 2.7
def output(text, *args, **kwargs):
    # type: (str, *Any, **IO[str]) -> None
    if args:
        text = text % args
    stream = kwargs.get("stream", sys.stdout)
    try:
        stream.write(text)
        stream.flush()
    except Exception:
        # TODO: Way to generic!
        pass  # avoid exception on broken pipe (e.g. due to | head)


# Output text if opt_verbose is set (-v). Adds no linefeed
def verbose(text, *args, **kwargs):
    # type: (str, *Any, **IO[str]) -> None
    if logger.isEnabledFor(VERBOSE):
        output(text, *args, **kwargs)


# Output text if, opt_verbose >= 2 (-vv).
def vverbose(text, *args, **kwargs):
    # type: (str, *Any, **IO[str]) -> None
    if logger.isEnabledFor(logging.DEBUG):
        verbose(text, *args, **kwargs)


#
# More top level wrappers
#


# TODO: Inconsistent -> Adds newline and other functions don't
def warning(text, *args, **kwargs):
    # type: (str, *Any, **IO[str]) -> None
    kwargs.setdefault("stream", sys.stderr)
    stripped = text.lstrip()
    indent = text[:len(text) - len(stripped)]
    wtext = "%s%s%sWARNING:%s %s\n" % (indent, tty.bold, tty.yellow, tty.normal, stripped)
    output(wtext, *args, **kwargs)


def error(text, *args):
    # type: (str, *Any) -> None
    output(text, *args, stream=sys.stderr)


def section_begin(text, **kwargs):
    # type: (str, **IO[str]) -> None
    verbose("%s%s%s:\n", tty.bold, text, tty.normal)


def section_success(text):
    # type: (str) -> None
    verbose("%sSUCCESS%s - %s\n", tty.green, tty.normal, text)


def section_error(text):
    # type: (str) -> None
    verbose("%sERROR%s - %s\n", tty.red, tty.normal, text)


def step(text):
    # type: (str) -> None
    verbose("%s+%s %s\n", tty.yellow, tty.normal, text.upper())

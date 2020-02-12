#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Utiliy module for holding generic methods that implement handling
of console input / output"""

import logging
import sys
from typing import Any, IO  # pylint: disable=unused-import

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

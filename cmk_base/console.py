#!/usr/bin/env python
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

import cmk.utils.tty as tty
import cmk.utils.log

# NOTE: This is a hack! We abuse the global logger just to pass around the
# verbosity setting.
logger = cmk.utils.log.get_logger("base")

#
# Generic / low level functions
#


# would rather use "def output(text, *args, stream=sys.stdout)", but this is not possible
# with python 2.7
def output(text, *args, **kwargs):
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
    if logger.is_verbose():
        output(text, *args, **kwargs)


# Output text if, opt_verbose >= 2 (-vv).
def vverbose(text, *args, **kwargs):
    if logger.isEnabledFor(logging.DEBUG):
        verbose(text, *args, **kwargs)


#
# More top level wrappers
#


# TODO: Inconsistent -> Adds newline and other functions don't
def warning(text, *args, **kwargs):
    kwargs.setdefault("stream", sys.stderr)

    stripped = text.lstrip()
    indent = text[:len(text) - len(stripped)]

    text = "%s%s%sWARNING:%s %s\n" % (indent, tty.bold, tty.yellow, tty.normal, stripped)

    output(text, *args, **kwargs)


def error(text, *args):
    output(text, *args, stream=sys.stderr)


def section_begin(text, *args, **kwargs):
    verbose(tty.bold + text + tty.normal + ":\n")


def section_success(text):
    verbose("%sSUCCESS%s - %s\n" % (tty.green, tty.normal, text))


def section_error(text):
    verbose("%sERROR%s - %s\n" % (tty.red, tty.normal, text))


def step(text):
    verbose("%s+%s %s\n" % (tty.yellow, tty.normal, text.upper()))


def step_error(text):
    verbose(text + "\n")

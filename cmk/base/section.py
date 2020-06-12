#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.tty as tty
import cmk.utils.log.console as console


# Note: section_begin|success|error|step is a naive and incomplete
# finite-state machine.  The four functions should be used together.
def section_begin(text):
    # type: (str) -> None
    console.verbose("%s%s%s:\n", tty.bold, text, tty.normal)


def section_success(text):
    # type: (str) -> None
    console.verbose("%sSUCCESS%s - %s\n", tty.green, tty.normal, text)


def section_error(text, verbose=True):
    # type: (str, bool) -> None
    if verbose:
        console.verbose("%s - %s\n", tty.error, text)
    else:
        console.info("%s - %s\n", tty.error, text)


def section_step(text, add_info="", verbose=True):
    # type: (str, str, bool) -> None
    if add_info:
        # Additional information, not titlecased
        add_info = " (%s)" % add_info

    if verbose:
        console.verbose("%s+%s %s%s\n", tty.yellow, tty.normal, text.upper(), add_info)
    else:
        console.info("%s+%s %s%s\n", tty.yellow, tty.normal, text.upper(), add_info)

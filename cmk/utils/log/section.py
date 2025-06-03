#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc import tty

from . import console


# Note: section_begin|success|error|step is a naive and incomplete
# finite-state machine.  The four functions should be used together.
def section_begin(text: str) -> None:
    console.verbose(f"{tty.bold}{text}{tty.normal}:")


def section_success(text: str) -> None:
    console.verbose(f"{tty.green}SUCCESS{tty.normal} - {text}")


def section_error(text: str, verbose: bool = True) -> None:
    if verbose:
        console.verbose(f"{tty.error} - {text}")
    else:
        console.info(f"{tty.error} - {text}")


def section_step(text: str, add_info: str = "", verbose: bool = True) -> None:
    if add_info:
        add_info = f" ({add_info})"  # Additional information, not titlecased
    if verbose:
        console.verbose(f"{tty.yellow}+{tty.normal} {text.upper()}{add_info}")
    else:
        console.info(f"{tty.yellow}+{tty.normal} {text.upper()}{add_info}")

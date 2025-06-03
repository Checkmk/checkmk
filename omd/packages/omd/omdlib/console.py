#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import sys

from cmk.ccc import tty


def ok() -> None:
    sys.stdout.write(tty.ok + "\n")


def show_success(exit_code: int) -> int:
    if exit_code is True or exit_code == 0:
        ok()
    else:
        sys.stdout.write(tty.error + "\n")
    return exit_code

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
import sys
from contextlib import suppress

from cmk.ccc import tty

import cmk.utils.paths
from cmk.utils.log import console


def print_(txt: str) -> None:
    with suppress(IOError):
        sys.stdout.write(txt)
        sys.stdout.flush()


def do_check_nagiosconfig() -> bool:
    """Execute nagios config verification to ensure the created check_mk_objects.cfg is valid"""
    command = [str(cmk.utils.paths.nagios_binary), "-vp", str(cmk.utils.paths.nagios_config_file)]
    console.verbose(f"Running '{subprocess.list2cmdline(command)}'")
    print_("Validating Nagios configuration...")

    completed_process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        encoding="utf-8",
        check=False,
    )
    if not completed_process.returncode:
        print_(tty.ok + "\n")
        return True

    print_("ERROR:\n")
    with suppress(IOError):
        sys.stderr.write(completed_process.stdout)
        sys.stdout.flush()
    return False

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
import sys

import cmk.base.obsolete_output as out
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.log import console


def do_check_nagiosconfig() -> bool:
    """Execute nagios config verification to ensure the created check_mk_objects.cfg is valid"""
    command = [cmk.utils.paths.nagios_binary, "-vp", cmk.utils.paths.nagios_config_file]
    console.verbose("Running '%s'\n" % subprocess.list2cmdline(command))
    out.output("Validating Nagios configuration...")

    p = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        encoding="utf-8",
    )
    stdout = p.communicate()[0]
    exit_status = p.returncode
    if not exit_status:
        out.output(tty.ok + "\n")
        return True

    out.output("ERROR:\n")
    out.output(stdout, stream=sys.stderr)
    return False

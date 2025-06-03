#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Handling of site-internal init scripts"""

import contextlib
import os
import subprocess
import sys
from typing import Literal

from cmk.ccc import tty

from cmk.utils.local_secrets import SiteInternalSecret
from cmk.utils.log.security_event import log_security_event, SiteStartStoppedEvent


def call_init_scripts(
    site_dir: str,
    command: Literal["start", "stop", "restart", "reload", "status"],
    daemon: str | None = None,
    exclude_daemons: list[str] | None = None,
) -> Literal[0, 2]:
    # Restart: Do not restart each service after another,
    # but first do stop all, then start all again! This
    # preserves the order.
    if command == "restart":
        log_security_event(SiteStartStoppedEvent(event="restart", daemon=daemon))
        code_stop = call_init_scripts(site_dir, "stop", daemon)
        code_start = call_init_scripts(site_dir, "start", daemon)
        return 0 if (code_stop, code_start) == (0, 0) else 2

    # OMD guarantees OMD_ROOT to be the current directory
    with contextlib.chdir(site_dir):
        if command == "start":
            log_security_event(SiteStartStoppedEvent(event="start", daemon=daemon))
            SiteInternalSecret().regenerate()
        elif command == "stop":
            log_security_event(SiteStartStoppedEvent(event="stop", daemon=daemon))

        if daemon:
            success = _call_init_script(f"{site_dir}/etc/init.d/{daemon}", command)

        else:
            # Call stop scripts in reverse order. If daemon is set,
            # then only that start script will be affected
            rc_dir, scripts = _init_scripts(site_dir)
            if command == "stop":
                scripts.reverse()
            success = True

            for script in scripts:
                if exclude_daemons and script in exclude_daemons:
                    continue

                if not _call_init_script(f"{rc_dir}/{script}", command):
                    success = False

    return 0 if success else 2


def check_status(
    site_dir: str,
    verbose: bool,
    display: bool = True,
    daemon: str | None = None,
    bare: bool = False,
) -> int:
    num_running = 0
    num_unused = 0
    num_stopped = 0
    rc_dir, scripts = _init_scripts(site_dir)
    components = [s.split("-", 1)[-1] for s in scripts]
    if daemon and daemon not in components:
        if not bare:
            sys.stderr.write("ERROR: This daemon does not exist.\n")
        return 3
    for script in scripts:
        komponent = script.split("/")[-1].split("-", 1)[-1]
        if daemon and komponent != daemon:
            continue

        state = subprocess.call(
            [os.path.join(rc_dir, script), "status"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if display and (state != 5 or verbose):
            if bare:
                sys.stdout.write(komponent + " ")
            else:
                sys.stdout.write("%-20s" % (komponent + ":"))
                sys.stdout.write(tty.bold)

        if bare:
            if state != 5 or verbose:
                sys.stdout.write("%d\n" % state)

        if state == 0:
            if display and not bare:
                sys.stdout.write(tty.green + "running\n")
            num_running += 1
        elif state == 5:
            if display and verbose and not bare:
                sys.stdout.write(tty.blue + "unused\n")
            num_unused += 1
        else:
            if display and not bare:
                sys.stdout.write(tty.red + "stopped\n")
            num_stopped += 1
        if display and not bare:
            sys.stdout.write(tty.normal)

    if num_stopped > 0 and num_running == 0:
        exit_code = 1
        ovstate = tty.red + "stopped"
    elif num_running > 0 and num_stopped == 0:
        exit_code = 0
        ovstate = tty.green + "running"
    elif num_running == 0 and num_stopped == 0:
        exit_code = 0
        ovstate = tty.blue + "unused"
    else:
        exit_code = 2
        ovstate = tty.yellow + "partially running"
    if display:
        if bare:
            sys.stdout.write("OVERALL %d\n" % exit_code)
        else:
            sys.stdout.write("---------------------------\n")
            sys.stdout.write("Overall state:      %s\n" % (tty.bold + ovstate + tty.normal))
    return exit_code


def _init_scripts(site_dir: str) -> tuple[str, list[str]]:
    rc_dir = f"{site_dir}/etc/rc.d"
    try:
        scripts = sorted(os.listdir(rc_dir))
        return rc_dir, scripts
    except Exception:
        return rc_dir, []


def _call_init_script(scriptpath: str, command: str) -> bool:
    if not os.path.exists(scriptpath):
        sys.stderr.write("ERROR: This daemon does not exist.\n")
        return False

    try:
        return subprocess.call([scriptpath, command]) in [0, 5]
    except OSError as e:
        sys.stderr.write(f"ERROR: Failed to run '{scriptpath}': {e}\n")
        return False

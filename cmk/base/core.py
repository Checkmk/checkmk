#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""All core related things like direct communication with the running core"""

import enum
import os
import subprocess
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Literal

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKBailOut, MKGeneralException
from cmk.utils.hostaddress import HostName

import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.nagios_utils
import cmk.base.obsolete_output as out
from cmk.base.core_config import MonitoringCore

# suppress "Cannot find module" error from mypy


# .
#   .--Control-------------------------------------------------------------.
#   |                   ____            _             _                    |
#   |                  / ___|___  _ __ | |_ _ __ ___ | |                   |
#   |                 | |   / _ \| '_ \| __| '__/ _ \| |                   |
#   |                 | |__| (_) | | | | |_| | | (_) | |                   |
#   |                  \____\___/|_| |_|\__|_|  \___/|_|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Invoke actions affecting the core like reload/restart                |
#   '----------------------------------------------------------------------'

_LockingMode = Literal["abort", "wait"] | None


class CoreAction(enum.Enum):
    START = "start"
    RESTART = "restart"
    RELOAD = "reload"
    STOP = "stop"


def do_reload(
    core: MonitoringCore,
    hosts_to_update: set[HostName] | None = None,
    *,
    locking_mode: _LockingMode,
    duplicates: Sequence[HostName],
) -> None:
    do_restart(
        core,
        action=CoreAction.RELOAD,
        hosts_to_update=hosts_to_update,
        locking_mode=locking_mode,
        duplicates=duplicates,
    )


def do_restart(
    core: MonitoringCore,
    action: CoreAction = CoreAction.RESTART,
    hosts_to_update: set[HostName] | None = None,
    *,
    locking_mode: _LockingMode,
    duplicates: Sequence[HostName],
    skip_config_locking_for_bakery: bool = False,
) -> None:
    try:
        with activation_lock(mode=locking_mode):
            core_config.do_create_config(
                core=core,
                config_cache=config.get_config_cache(),
                hosts_to_update=hosts_to_update,
                duplicates=duplicates,
                skip_config_locking_for_bakery=skip_config_locking_for_bakery,
            )
            do_core_action(action, monitoring_core=core.name())

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKBailOut("An error occurred: %s" % e)


# TODO: The store.lock_checkmk_configuration is doing something similar. It looks like we
# should unify these both locks. But: The lock_checkmk_configuration is currently acquired by the
# GUI process. In case the GUI calls an automation process, we would have a dead lock of these two
# processes. We'll have to check whether or not we can move the locking.
@contextmanager
def activation_lock(mode: Literal["abort", "wait"] | None) -> Iterator[None]:
    """Try to acquire the activation lock and raise exception in case it was not possible"""
    if mode is None:
        # TODO: We really should purge this strange case from being configurable
        yield None  # No locking at all
        return

    lock_file = cmk.utils.paths.default_config_dir + "/main.mk"

    if mode == "abort":
        with store.try_locked(lock_file) as result:
            if result is False:
                raise MKBailOut("Other restart currently in progress. Aborting.")
            yield None
        return

    if mode == "wait":
        with store.locked(lock_file):
            yield None
        return

    raise ValueError(f"Invalid lock mode: {mode}")


def do_core_action(
    action: CoreAction,
    monitoring_core: Literal["nagios", "cmc"],
    quiet: bool = False,
) -> None:
    if not quiet:
        out.output("%sing monitoring core..." % action.value.title())

    if monitoring_core == "nagios":
        os.putenv("CORE_NOVERIFY", "yes")
        command = ["%s/etc/init.d/core" % cmk.utils.paths.omd_root, action.value]
    else:
        command = ["omd", action.value, "cmc"]

    completed_process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        check=False,
    )
    if completed_process.returncode != 0:
        if not quiet:
            out.output("ERROR: %r\n" % completed_process.stdout)
        raise MKGeneralException(
            f"Cannot {action.value} the monitoring core: {completed_process.stdout!r}"
        )
    if not quiet:
        out.output(tty.ok + "\n")

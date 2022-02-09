#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""All core related things like direct communication with the running core"""

import enum
import os
import subprocess
from contextlib import contextmanager
from typing import Iterator, Optional

# suppress "Cannot find module" error from mypy
import livestatus

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.exceptions import MKBailOut, MKGeneralException, MKTimeout
from cmk.utils.type_defs import HostsToUpdate, TimeperiodName

import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.nagios_utils
import cmk.base.obsolete_output as out
from cmk.base.core_config import MonitoringCore

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


class CoreAction(enum.Enum):
    START = "start"
    RESTART = "restart"
    RELOAD = "reload"
    STOP = "stop"


def do_reload(
    core: MonitoringCore,
    hosts_to_update: HostsToUpdate = None,
) -> None:
    do_restart(core, action=CoreAction.RELOAD, hosts_to_update=hosts_to_update)


def do_restart(
    core: MonitoringCore,
    action: CoreAction = CoreAction.RESTART,
    hosts_to_update: HostsToUpdate = None,
) -> None:
    try:
        with activation_lock(mode=config.restart_locking):
            core_config.do_create_config(core, hosts_to_update=hosts_to_update)
            do_core_action(action)

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKBailOut("An error occurred: %s" % e)


# TODO: The store.lock_checkmk_configuration is doing something similar. It looks like we
# should unify these both locks. But: The lock_checkmk_configuration is currently acquired by the
# GUI process. In case the GUI calls an automation process, we would have a dead lock of these two
# processes. We'll have to check whether or not we can move the locking.
@contextmanager
def activation_lock(mode: Optional[str]) -> Iterator[None]:
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


def do_core_action(action: CoreAction, quiet: bool = False) -> None:
    if not quiet:
        out.output("%sing monitoring core..." % action.value.title())

    if config.monitoring_core == "nagios":
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
            "Cannot %s the monitoring core: %r" % (action.value, completed_process.stdout)
        )
    if not quiet:
        out.output(tty.ok + "\n")


# .
#   .--Timeperiods---------------------------------------------------------.
#   |      _____ _                                _           _            |
#   |     |_   _(_)_ __ ___   ___ _ __   ___ _ __(_) ___   __| |___        |
#   |       | | | | '_ ` _ \ / _ \ '_ \ / _ \ '__| |/ _ \ / _` / __|       |
#   |       | | | | | | | | |  __/ |_) |  __/ |  | | (_) | (_| \__ \       |
#   |       |_| |_|_| |_| |_|\___| .__/ \___|_|  |_|\___/ \__,_|___/       |
#   |                            |_|                                       |
#   +----------------------------------------------------------------------+
#   | Fetching timeperiods from the core                                   |
#   '----------------------------------------------------------------------'


def check_timeperiod(timeperiod: TimeperiodName) -> bool:
    """Check if a timeperiod is currently active. We have no other way than
    doing a Livestatus query. This is not really nice, but if you have a better
    idea, please tell me..."""
    # Let exceptions happen, they will be handled upstream.
    try:
        update_timeperiods_cache()
    except MKTimeout:
        raise

    except Exception:
        if cmk.utils.debug.enabled():
            raise

        # If the query is not successful better skip this check then fail
        return True

    # Note: This also returns True when the timeperiod is unknown
    #       The following function timeperiod_active handles this differently
    return _config_cache.get("timeperiods_cache").get(timeperiod, True)


def timeperiod_active(timeperiod: TimeperiodName) -> Optional[bool]:
    """Returns
    True : active
    False: inactive
    None : unknown timeperiod

    Raises an exception if e.g. a timeout or connection error appears.
    This way errors can be handled upstream."""
    update_timeperiods_cache()
    return _config_cache.get("timeperiods_cache").get(timeperiod)


def update_timeperiods_cache() -> None:
    # { "last_update": 1498820128, "timeperiods": [{"24x7": True}] }
    # The value is store within the config cache since we need a fresh start on reload
    tp_cache = _config_cache.get("timeperiods_cache")

    if not tp_cache:
        response = livestatus.LocalConnection().query("GET timeperiods\nColumns: name in")
        for tp_name, tp_active in response:
            tp_cache[tp_name] = bool(tp_active)


def cleanup_timeperiod_caches() -> None:
    _config_cache.get("timeperiods_cache").clear()


cmk.utils.cleanup.register_cleanup(cleanup_timeperiod_caches)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""All core related things like direct communication with the running core"""

import fcntl
import os
import subprocess
import sys
from typing import Optional
import enum

import cmk.utils.paths
import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKTimeout, MKBailOut
from cmk.utils.log import console
from cmk.utils.type_defs import TimeperiodName

import cmk.base.obsolete_output as out
import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.nagios_utils
from cmk.base.caching import config_cache as _config_cache
from cmk.base.core_config import MonitoringCore

# suppress "Cannot find module" error from mypy
import livestatus

_restart_lock_fd = None

#.
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


def do_reload(core: MonitoringCore) -> None:
    do_restart(core, action=CoreAction.RELOAD)


# TODO: Cleanup duplicate code with automation_restart()
def do_restart(core: MonitoringCore, action: CoreAction = CoreAction.RESTART) -> None:
    try:
        if try_get_activation_lock():
            raise MKBailOut("Other restart currently in progress. Aborting.")

        with core_config.backup_objects_file(core):
            try:
                core_config.do_create_config(core, with_agents=True)
            except Exception as e:
                if cmk.utils.debug.enabled():
                    raise
                raise MKGeneralException("Error creating configuration: %s" % e)

        core.precompile()
        do_core_action(action)

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKBailOut("An error occurred: %s" % e)


def try_get_activation_lock() -> bool:
    global _restart_lock_fd
    # In some bizarr cases (as cmk -RR) we need to avoid duplicate locking!
    if config.restart_locking and _restart_lock_fd is None:
        lock_file = cmk.utils.paths.default_config_dir + "/main.mk"
        _restart_lock_fd = os.open(lock_file, os.O_RDONLY)
        # Make sure that open file is not inherited to monitoring core!
        fcntl.fcntl(_restart_lock_fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        try:
            console.verbose("Waiting for exclusive lock on %s.\n" % lock_file, stream=sys.stderr)
            fcntl.flock(_restart_lock_fd,
                        fcntl.LOCK_EX | (config.restart_locking == "abort" and fcntl.LOCK_NB or 0))
        except Exception:
            return True
    return False


def do_core_action(action: CoreAction, quiet: bool = False) -> None:
    if not quiet:
        out.output("%sing monitoring core..." % action.value.title())

    if config.monitoring_core == "nagios":
        os.putenv("CORE_NOVERIFY", "yes")
        command = ["%s/etc/init.d/core" % cmk.utils.paths.omd_root, action.value]
    else:
        command = ["omd", action.value, "cmc"]

    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    result = p.wait()
    if result != 0:
        assert p.stdout is not None
        output = p.stdout.read()
        if not quiet:
            out.output("ERROR: %r\n" % output)
        raise MKGeneralException("Cannot %s the monitoring core: %r" % (action.value, output))
    if not quiet:
        out.output(tty.ok + "\n")


#.
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
    return _config_cache.get_dict("timeperiods_cache").get(timeperiod, True)


def timeperiod_active(timeperiod: TimeperiodName) -> Optional[bool]:
    """Returns
    True : active
    False: inactive
    None : unknown timeperiod

    Raises an exception if e.g. a timeout or connection error appears.
    This way errors can be handled upstream."""
    update_timeperiods_cache()
    return _config_cache.get_dict("timeperiods_cache").get(timeperiod)


def update_timeperiods_cache() -> None:
    # { "last_update": 1498820128, "timeperiods": [{"24x7": True}] }
    # The value is store within the config cache since we need a fresh start on reload
    tp_cache = _config_cache.get_dict("timeperiods_cache")

    if not tp_cache:
        response = livestatus.LocalConnection().query("GET timeperiods\nColumns: name in")
        for tp_name, tp_active in response:
            tp_cache[tp_name] = bool(tp_active)


def cleanup_timeperiod_caches() -> None:
    _config_cache.get_dict("timeperiods_cache").clear()


cmk.utils.cleanup.register_cleanup(cleanup_timeperiod_caches)

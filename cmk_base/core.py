#!/usr/bin/python
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
"""All core related things like direct communication with the running core"""

import fcntl
import os
import subprocess
import sys
import errno

import cmk.utils.paths
import cmk.utils.debug
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKTimeout

import cmk_base.console as console
import cmk_base.config as config
import cmk_base.core_config as core_config
import cmk_base.nagios_utils
from cmk_base import config_cache
import cmk_base.cleanup

# suppress "Cannot find module" error from mypy
import livestatus  # type: ignore

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


def do_reload(core):
    do_restart(core, only_reload=True)


# TODO: Cleanup duplicate code with automation_restart()
def do_restart(core, only_reload=False):
    try:
        backup_path = None

        if try_get_activation_lock():
            # TODO: Replace by MKBailOut()/MKTerminate()?
            console.error("Other restart currently in progress. Aborting.\n")
            sys.exit(1)

        # Save current configuration
        if os.path.exists(cmk.utils.paths.nagios_objects_file):
            backup_path = cmk.utils.paths.nagios_objects_file + ".save"
            console.verbose(
                "Renaming %s to %s\n",
                cmk.utils.paths.nagios_objects_file,
                backup_path,
                stream=sys.stderr)
            os.rename(cmk.utils.paths.nagios_objects_file, backup_path)
        else:
            backup_path = None

        try:
            core_config.do_create_config(core, with_agents=True)
        except Exception as e:
            # TODO: Replace by MKBailOut()/MKTerminate()?
            console.error("Error creating configuration: %s\n" % e)
            if backup_path:
                os.rename(backup_path, cmk.utils.paths.nagios_objects_file)
            if cmk.utils.debug.enabled():
                raise
            sys.exit(1)

        if config.monitoring_core == "cmc" or cmk_base.nagios_utils.do_check_nagiosconfig():
            if backup_path:
                os.remove(backup_path)

            core.precompile()

            do_core_action(only_reload and "reload" or "restart")
        else:
            # TODO: Replace by MKBailOut()/MKTerminate()?
            console.error("Configuration for monitoring core is invalid. Rolling back.\n")

            broken_config_path = "%s/check_mk_objects.cfg.broken" % cmk.utils.paths.tmp_dir
            file(broken_config_path, "w").write(file(cmk.utils.paths.nagios_objects_file).read())
            console.error(
                "The broken file has been copied to \"%s\" for analysis.\n" % broken_config_path)

            if backup_path:
                os.rename(backup_path, cmk.utils.paths.nagios_objects_file)
            else:
                os.remove(cmk.utils.paths.nagios_objects_file)
            sys.exit(1)

    except Exception as e:
        if backup_path:
            try:
                os.remove(backup_path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
        if cmk.utils.debug.enabled():
            raise
        # TODO: Replace by MKBailOut()/MKTerminate()?
        console.error("An error occurred: %s\n" % e)
        sys.exit(1)


def try_get_activation_lock():
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


# Action can be restart, reload, start or stop
def do_core_action(action, quiet=False):
    if not quiet:
        console.output("%sing monitoring core..." % action.title())

    if config.monitoring_core == "nagios":
        os.putenv("CORE_NOVERIFY", "yes")
        command = ["%s/etc/init.d/core" % cmk.utils.paths.omd_root, action]
    else:
        command = ["omd", action, "cmc"]

    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    result = p.wait()
    if result != 0:
        output = p.stdout.read()
        if not quiet:
            console.output("ERROR: %s\n" % output)
        raise MKGeneralException("Cannot %s the monitoring core: %s" % (action, output))
    else:
        if not quiet:
            console.output(tty.ok + "\n")


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


# Check if a timeperiod is currently active. We have no other way than
# doing a Livestatus query. This is not really nice, but if you have a better
# idea, please tell me...
def check_timeperiod(timeperiod):
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
    return config_cache.get_dict("timeperiods_cache").get(timeperiod, True)


# Returns
# True : active
# False: inactive
# None : unknown timeperiod
#
# Raises an exception if e.g. a timeout or connection error appears.
# This way errors can be handled upstream.
def timeperiod_active(timeperiod):
    update_timeperiods_cache()
    return config_cache.get_dict("timeperiods_cache").get(timeperiod)


def update_timeperiods_cache():
    # { "last_update": 1498820128, "timeperiods": [{"24x7": True}] }
    # The value is store within the config cache since we need a fresh start on reload
    tp_cache = config_cache.get_dict("timeperiods_cache")

    if not tp_cache:
        response = livestatus.LocalConnection().query("GET timeperiods\nColumns: name in")
        for tp_name, tp_active in response:
            tp_cache[tp_name] = bool(tp_active)


def cleanup_timeperiod_caches():
    config_cache.get_dict("timeperiods_cache").clear()


cmk_base.cleanup.register_cleanup(cleanup_timeperiod_caches)

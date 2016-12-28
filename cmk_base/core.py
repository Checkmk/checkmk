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
import socket
import sys

import cmk.paths
import cmk.debug
import cmk.tty as tty
from cmk.exceptions import MKGeneralException

import cmk_base.console as console
import cmk_base.config as config
import cmk_base.core_config as core_config
import cmk_base.core_nagios as core_nagios
from cmk_base.exceptions import MKTimeout

try:
    import cmk_base.cee.core_cmc as core_cmc
except ImportError:
    core_cmc = None

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

def do_reload():
    do_restart(True)


# TODO: Cleanup duplicate code with automation_restart()
def do_restart(only_reload = False):
    try:
        backup_path = None

        if try_get_activation_lock():
            # TODO: Replace by MKBailOut()/MKTerminate()?
            console.error("Other restart currently in progress. Aborting.\n")
            sys.exit(1)

        # Save current configuration
        if os.path.exists(cmk.paths.nagios_objects_file):
            backup_path = cmk.paths.nagios_objects_file + ".save"
            console.verbose("Renaming %s to %s\n", cmk.paths.nagios_objects_file, backup_path, stream=sys.stderr)
            os.rename(cmk.paths.nagios_objects_file, backup_path)
        else:
            backup_path = None

        try:
            core_config.do_create_config(with_agents=True)
        except Exception, e:
            # TODO: Replace by MKBailOut()/MKTerminate()?
            console.error("Error creating configuration: %s\n" % e)
            if backup_path:
                os.rename(backup_path, cmk.paths.nagios_objects_file)
            if cmk.debug.enabled():
                raise
            sys.exit(1)

        if config.monitoring_core == "cmc" or core_nagios.do_check_nagiosconfig():
            if backup_path:
                os.remove(backup_path)

            core_config.precompile()

            do_core_action(only_reload and "reload" or "restart")
        else:
            # TODO: Replace by MKBailOut()/MKTerminate()?
            console.error("Configuration for monitoring core is invalid. Rolling back.\n")

            broken_config_path = "%s/check_mk_objects.cfg.broken" % cmk.paths.tmp_dir
            file(broken_config_path, "w").write(file(cmk.paths.nagios_objects_file).read())
            console.error("The broken file has been copied to \"%s\" for analysis.\n" % broken_config_path)

            if backup_path:
                os.rename(backup_path, cmk.paths.nagios_objects_file)
            else:
                os.remove(cmk.paths.nagios_objects_file)
            sys.exit(1)

    except Exception, e:
        try:
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
        except:
            pass
        if cmk.debug.enabled():
            raise
        # TODO: Replace by MKBailOut()/MKTerminate()?
        console.error("An error occurred: %s\n" % e)
        sys.exit(1)


def try_get_activation_lock():
    global _restart_lock_fd
    # In some bizarr cases (as cmk -RR) we need to avoid duplicate locking!
    if config.restart_locking and _restart_lock_fd == None:
        lock_file = cmk.paths.default_config_dir + "/main.mk"
        _restart_lock_fd = os.open(lock_file, os.O_RDONLY)
        # Make sure that open file is not inherited to monitoring core!
        fcntl.fcntl(_restart_lock_fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        try:
            console.verbose("Waiting for exclusive lock on %s.\n" % lock_file, stream=sys.stderr)
            fcntl.flock(_restart_lock_fd, fcntl.LOCK_EX |
                ( config.restart_locking == "abort" and fcntl.LOCK_NB or 0))
        except:
            return True
    return False


# Action can be restart, reload, start or stop
def do_core_action(action, quiet=False):
    if not quiet:
        console.output("%sing monitoring core..." % action.title())

    if config.monitoring_core == "nagios":
        os.putenv("CORE_NOVERIFY", "yes")
        command = cmk.paths.nagios_startscript + " %s 2>&1" % action
    else:
        command = "omd %s cmc 2>&1" % action

    process = os.popen(command, "r")
    output = process.read()
    if process.close():
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

g_inactive_timerperiods = None # Cache for current state of timeperiods

# Return plain response from local Livestatus - without any parsing
# TODO: Use livestatus module
def simple_livestatus_query(lql):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(cmk.paths.livestatus_unix_socket)
    # We just get the currently inactive timeperiods. All others
    # (also non-existing) are considered to be active
    s.send(lql)
    s.shutdown(socket.SHUT_WR)
    response = ""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        response += chunk
    return response


# Check if a timeperiod is currently active. We have no other way than
# doing a Livestatus query. This is not really nice, but if you have a better
# idea, please tell me...
def check_timeperiod(timeperiod):
    global g_inactive_timerperiods
    # Let exceptions happen, they will be handled upstream.
    if g_inactive_timerperiods == None:
        try:
            response = simple_livestatus_query("GET timeperiods\nColumns: name\nFilter: in = 0\n")
            g_inactive_timerperiods = response.splitlines()
        except MKTimeout:
            raise

        except:
            if cmk.debug.enabled():
                raise
            else:
                # If the query is not successful better skip this check then fail
                return True

    return timeperiod not in g_inactive_timerperiods


def cleanup_inactive_timeperiods():
    global g_inactive_timerperiods
    g_inactive_timerperiods = None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.0.0p21"

import os
import sys
import time
import signal
try:
    import configparser
except ImportError:  # Python 2
    import ConfigParser as configparser  # type: ignore

try:
    from typing import Dict, List, Any, Set
except ImportError:
    pass

try:
    # TODO: We should probably ship this package.
    import pyinotify  # type: ignore[import] # pylint: disable=import-error
except ImportError:
    sys.stderr.write("Error: Python plugin pyinotify is not installed\n")
    sys.exit(1)


def usage():
    sys.stdout.write("Usage: mk_inotify [-g]\n")
    sys.stdout.write("         -g: run in foreground\n\n")


# Available options:
# -g: run in foreground
opt_foreground = False
if len(sys.argv) == 2 and sys.argv[1] == "-g":
    opt_foreground = True

mk_confdir = os.getenv("MK_CONFDIR") or "/etc/check_mk"
mk_vardir = os.getenv("MK_VARDIR") or "/var/lib/check_mk_agent"

config_filename = mk_confdir + "/mk_inotify.cfg"
configured_paths = mk_vardir + "/mk_inotify.configured"
pid_filename = mk_vardir + "/mk_inotify.pid"

config = configparser.SafeConfigParser({})
if not os.path.exists(config_filename):
    sys.exit(0)
config_mtime = os.stat(config_filename).st_mtime
config.read(config_filename)

# Configurable in Agent Bakery
heartbeat_timeout = config.getint("global", "heartbeat_timeout")
write_interval = config.getint("global", "write_interval")
max_messages_per_interval = config.getint("global", "max_messages_per_interval")
stats_retention = config.getint("global", "stats_retention")
config.remove_section("global")


def output_data():
    sys.stdout.write("<<<inotify:sep(9)>>>\n")
    if os.path.exists(configured_paths):
        sys.stdout.write(open(configured_paths).read())

    now = time.time()
    for dirpath, _unused_dirnames, filenames in os.walk(mk_vardir):
        for filename in filenames:
            if filename.startswith("mk_inotify.stats"):
                try:
                    the_file = "%s/%s" % (dirpath, filename)
                    filetime = os.stat(the_file).st_mtime
                    file_age = now - filetime
                    if file_age > 5:
                        sys.stdout.write(open(the_file).read())
                    if file_age > stats_retention:
                        os.unlink(the_file)
                except Exception:
                    pass
        break


# Check if another mk_inotify process is already running
if os.path.exists(pid_filename):
    pid_str = open(pid_filename).read()
    proc_cmdline = "/proc/%s/cmdline" % pid_str
    if os.path.exists(proc_cmdline):
        cmdline = open(proc_cmdline).read()
        cmdline_tokens = cmdline.split("\0")
        if "mk_inotify" in cmdline_tokens[1]:
            # Another mk_notify process is already running..
            # Simply output the current statistics and exit
            output_data()

            # The pidfile is also the heartbeat file for the running process
            os.utime(pid_filename, None)
            sys.exit(0)

#   .--Fork----------------------------------------------------------------.
#   |                         _____          _                             |
#   |                        |  ___|__  _ __| | __                         |
#   |                        | |_ / _ \| '__| |/ /                         |
#   |                        |  _| (_) | |  |   <                          |
#   |                        |_|  \___/|_|  |_|\_\                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   Reaching this point means that no mk_inotify is currently running

if not opt_foreground:
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        # Decouple from parent environment
        os.chdir("/")
        os.umask(0)
        os.setsid()

        # Close all fd
        for fd in range(0, 256):
            try:
                os.close(fd)
            except OSError:
                pass
    except Exception as e:
        sys.stderr.write("Error forking mk_inotify: %s" % e)

    # Save pid of working process.
    open(pid_filename, "w").write("%d" % os.getpid())
#.
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Computed configuration
folder_configs = {}  # type: Dict[str, Dict[str, Any]]
# Data to be written to disk
output = []  # type: List[str]


def get_watched_files():
    files = set([])
    for folder, attributes in folder_configs.items():
        for filenames in attributes["monitor_files"].values():
            for filename in filenames:
                files.add("configured\tfile\t%s/%s" % (folder, filename))
        if attributes.get("monitor_all"):
            files.add("configured\tfolder\t%s" % (folder))
    return files


def wakeup_handler(signum, frame):
    global output
    if output:
        if opt_foreground:
            sys.stdout.write("%s\n" % "\n".join(output))
            sys.stdout.write("%s\n" % "\n".join(get_watched_files()))
        else:
            filename = "mk_inotify.stats.%d" % time.time()
            open("%s/%s" % (mk_vardir, filename), "w").write("\n".join(output) + "\n")
        output = []

    # Check if configuration has changed -> restart
    if config_mtime != os.stat(config_filename).st_mtime:
        os.execv(__file__, sys.argv)

    # Exit on various instances
    if not opt_foreground:
        if not os.path.exists(pid_filename):  # pidfile is missing
            sys.exit(0)
        if time.time() - os.stat(pid_filename).st_mtime > heartbeat_timeout:  # heartbeat timeout
            sys.exit(0)
        if os.getpid() != int(open(pid_filename).read()):  # pidfile differs
            sys.exit(0)

    update_watched_folders()
    signal.alarm(write_interval)


def do_output(what, event):
    if event.dir:
        return  # Only monitor files

    if len(output) > max_messages_per_interval:
        last_message = "warning\tMaximum messages reached: %d per %d seconds" % \
                    (max_messages_per_interval, write_interval)
        if output[-1] != last_message:
            output.append(last_message)
        return

    path = event.path
    path_config = folder_configs.get(path)
    if not path_config:
        return  # shouldn't happen, maybe on subfolders (not supported)

    filename = os.path.basename(event.pathname)
    if what in path_config["monitor_all"] or\
       filename in path_config["monitor_files"].get(what, []):
        line = "%d\t%s\t%s" % (time.time(), what, event.pathname)
        if map_events[what][1]:  # Check if filestats are enabled
            try:
                stats = os.stat(event.pathname)
                line += "\t%d\t%d" % (stats.st_size, stats.st_mtime)
            except Exception:
                pass
        output.append(line)
        if opt_foreground:
            sys.stdout.write("%s\n" % line)


map_events = {
    # Mode     Mask                        Report_filestats (currently unused)
    "access": (pyinotify.IN_ACCESS, False),
    "open": (pyinotify.IN_OPEN, False),
    "create": (pyinotify.IN_CREATE, False),
    "delete": (pyinotify.IN_DELETE, False),
    "modify": (pyinotify.IN_MODIFY, False),
    "movedto": (pyinotify.IN_MOVED_TO, False),
    "movedfrom": (pyinotify.IN_MOVED_FROM, False),
    "moveself": (pyinotify.IN_MOVE_SELF, False),
}


class NotifyEventHandler(pyinotify.ProcessEvent):
    def process_IN_MOVED_TO(self, event):
        do_output("movedto", event)

    def process_IN_MOVED_FROM(self, event):
        do_output("movedfrom", event)

    def process_IN_MOVE_SELF(self, event):
        do_output("moveself", event)
#    def process_IN_CLOSE_NOWRITE(self, event):
#        print "CLOSE_NOWRITE event:", event.pathname
#
#    def process_IN_CLOSE_WRITE(self, event):
#        print "CLOSE_WRITE event:", event.pathname

    def process_IN_CREATE(self, event):
        do_output("create", event)

    def process_IN_DELETE(self, event):
        do_output("delete", event)

    def process_IN_MODIFY(self, event):
        do_output("modify", event)

    def process_IN_OPEN(self, event):
        do_output("open", event)


# Watch manager
wm = pyinotify.WatchManager()


def update_watched_folders():
    for folder, attributes in folder_configs.items():
        if attributes.get("watch_descriptor"):
            if not wm.get_path(attributes["watch_descriptor"].get(folder)):
                del attributes["watch_descriptor"]
        else:
            if os.path.exists(folder):
                new_wd = wm.add_watch(folder, attributes["mask"], rec=True)
                if new_wd.get(folder) > 0:
                    attributes["watch_descriptor"] = new_wd


def main():
    # Read config

    for section in config.sections():
        section_tokens = section.split("|")

        folder = section_tokens[0]
        folder_configs.setdefault(folder, {
            "add_modes": {},
            "del_modes": {},
            "all_add_modes": set([]),
            "all_del_modes": set([])
        })

        files = None
        if len(section_tokens) > 1:
            files = set(section_tokens[1:])

        add_modes = set([])
        del_modes = set([])
        for key, value in config.items(section):
            if key in map_events:
                if value == "1":
                    add_modes.add(key)
                else:
                    del_modes.add(key)

        if files:
            for mode in add_modes:
                folder_configs[folder]["add_modes"].setdefault(mode, set([]))
                folder_configs[folder]["add_modes"][mode].update(files)
            for mode in del_modes:
                folder_configs[folder]["del_modes"].setdefault(mode, set([]))
                folder_configs[folder]["del_modes"][mode].update(files)
        else:
            folder_configs[folder]["all_add_modes"].update(add_modes)
            folder_configs[folder]["all_del_modes"].update(del_modes)

    # Evaluate config
    for folder, attributes in folder_configs.items():
        required_modes = set([])
        for mode in attributes["add_modes"].keys():
            if mode not in attributes["all_del_modes"]:
                required_modes.add(mode)

        files_to_monitor = {}  # type: Dict[str, Set]
        skip_modes = set([])
        for mode in required_modes:
            files_to_monitor.setdefault(mode, set([]))
            files_to_monitor[mode].update(attributes["add_modes"][mode])
            files_to_monitor[mode] -= attributes["del_modes"].get(mode, set([]))
            if not files_to_monitor[mode]:
                skip_modes.add(mode)

        attributes["monitor_files"] = files_to_monitor
        attributes["monitor_all"] = attributes["all_add_modes"] - attributes["all_del_modes"]
        attributes["modes"] = required_modes - skip_modes

        # Determine mask
        attributes["mask"] = 0
        for mode in attributes["modes"]:
            attributes["mask"] |= map_events[mode][0]
        for mode in attributes["monitor_all"]:
            attributes["mask"] |= map_events[mode][0]

    update_watched_folders()
    if opt_foreground:
        import pprint
        sys.stdout.write(pprint.pformat(folder_configs))

    # Save monitored file/folder information specified in mk_inotify.cfg
    open(configured_paths, "w").write("\n".join(get_watched_files()) + "\n")

    # Event handler
    eh = NotifyEventHandler()
    notifier = pyinotify.Notifier(wm, eh)

    # Wake up every few seconds, check heartbeat and write data to disk
    signal.signal(signal.SIGALRM, wakeup_handler)
    signal.alarm(write_interval)

    notifier.loop()


if __name__ == '__main__':
    main()

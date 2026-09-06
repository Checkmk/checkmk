#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

__version__ = "3.0.0b1"

import argparse
import configparser
import contextlib
import os
import signal
import sys
import time
from collections import namedtuple

try:
    from collections.abc import Mapping
    from typing import Any

    _ = Mapping, Any  # make ruff happy
except ImportError:
    pass

try:
    # TODO: We should probably ship this package.
    import pyinotify  # type: ignore[import-not-found]
except ImportError:
    pyinotify = None


def parse_arguments(argv):
    # type: (list[str]) -> argparse.Namespace
    parser = argparse.ArgumentParser(prog="mk_inotify")
    parser.add_argument("-g", "--foreground", action="store_true", help="run in foreground")
    return parser.parse_args(argv)


DEFAULT_CONFDIR = "/etc/check_mk"
DEFAULT_VARDIR = "/var/lib/check_mk_agent"

Paths = namedtuple("Paths", ["config_file", "configured_paths", "pid_file", "vardir"])


def get_paths(environ):
    # type: (Mapping[str, str]) -> Paths
    confdir = environ.get("MK_CONFDIR") or DEFAULT_CONFDIR
    vardir = environ.get("MK_VARDIR") or DEFAULT_VARDIR
    return Paths(
        config_file=confdir + "/mk_inotify.cfg",
        configured_paths=vardir + "/mk_inotify.configured",
        pid_file=vardir + "/mk_inotify.pid",
        vardir=vardir,
    )


# Configurable in Agent Bakery
GlobalSettings = namedtuple(
    "GlobalSettings",
    ["heartbeat_timeout", "write_interval", "max_messages_per_interval", "stats_retention"],
)


def read_global_settings(config):
    # type: (configparser.ConfigParser) -> GlobalSettings
    return GlobalSettings(
        heartbeat_timeout=config.getint("global", "heartbeat_timeout"),
        write_interval=config.getint("global", "write_interval"),
        max_messages_per_interval=config.getint("global", "max_messages_per_interval"),
        stats_retention=config.getint("global", "stats_retention"),
    )


def output_data(vardir, configured_paths, stats_retention, now):
    # type: (str, str, int, float) -> None
    sys.stdout.write("<<<inotify:sep(9)>>>\n")
    if os.path.exists(configured_paths):
        with open(configured_paths) as opened_conf_paths:
            sys.stdout.write(opened_conf_paths.read())

    for dirpath, _unused_dirnames, filenames in os.walk(vardir):
        for filename in filenames:
            if filename.startswith("mk_inotify.stats"):
                try:
                    the_file = "%s/%s" % (dirpath, filename)
                    filetime = os.stat(the_file).st_mtime
                    file_age = now - filetime
                    if file_age > 5:
                        with open(the_file) as opened_the_file:
                            sys.stdout.write(opened_the_file.read())
                    if file_age > stats_retention:
                        os.unlink(the_file)
                except Exception:
                    pass
        break


def is_other_instance_running(pid_file, proc_dir="/proc"):
    # type: (str, str) -> bool
    """Check if another mk_inotify process is already running

    A pid file that does not belong to a running mk_inotify process is removed.
    """
    if not os.path.exists(pid_file):
        return False
    with open(pid_file) as opened_file:
        pid_str = opened_file.read()
    proc_cmdline = "%s/%s/cmdline" % (proc_dir, pid_str)
    # make sure that the process with that ID is still running, else cleanup.
    if not os.path.exists(proc_cmdline):
        os.remove(pid_file)
        return False
    with open(proc_cmdline) as opened_inner_file:
        cmdline = opened_inner_file.read()
    # make sure that the process actually belongs to agent plugin command, else cleanup.
    if "mk_inotify" not in cmdline:
        os.remove(pid_file)
        return False
    return True


#   .--Fork----------------------------------------------------------------.
#   |                         _____          _                             |
#   |                        |  ___|__  _ __| | __                         |
#   |                        | |_ / _ \| '__| |/ /                         |
#   |                        |  _| (_) | |  |   <                          |
#   |                        |_|  \___/|_|  |_|\_\                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def daemonize(pid_file):
    # type: (str) -> None
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        # Decouple from parent environment
        os.chdir("/")
        os.setsid()

        # Close all fd
        for fd in range(256):
            with contextlib.suppress(OSError):
                os.close(fd)
    except Exception as e:
        sys.stderr.write("Error forking mk_inotify: %s" % e)

    # Save pid of working process.
    with open(pid_file, "w") as opened_file:
        opened_file.write("%d" % os.getpid())


# .
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def get_watched_files(folder_configs):  # type: ignore[explicit-any]
    # type: (Mapping[str, dict[str, Any]]) -> set[str]
    files = set()
    for folder, attributes in folder_configs.items():
        for filenames in attributes["monitor_files"].values():
            for filename in filenames:
                files.add("configured\tfile\t%s/%s" % (folder, filename))
        if attributes.get("monitor_all"):
            files.add("configured\tfolder\t%s" % (folder))
    return files


class Monitor:
    """Runtime state of the running plug-in"""

    def __init__(  # type: ignore[explicit-any]
        self, folder_configs, settings, paths, foreground, watch_manager, config_mtime
    ):
        # type: (dict[str, dict[str, Any]], GlobalSettings, Paths, bool, pyinotify.WatchManager, float) -> None
        self.folder_configs = folder_configs
        self.settings = settings
        self.paths = paths
        self.foreground = foreground
        self.watch_manager = watch_manager
        self.config_mtime = config_mtime
        # Data to be written to disk
        self.output = []  # type: list[str]

    def flush(self, now):
        # type: (float) -> None
        if not self.output:
            return
        if self.foreground:
            sys.stdout.write("%s\n" % "\n".join(self.output))
            sys.stdout.write("%s\n" % "\n".join(get_watched_files(self.folder_configs)))
        else:
            filename = "mk_inotify.stats.%d" % now
            with open("%s/%s" % (self.paths.vardir, filename), "w") as stats_file:
                stats_file.write("\n".join(self.output) + "\n")
        self.output = []

    def wakeup(self, signum, frame):  # noqa: ARG002
        # type: (int, object) -> None
        self.flush(time.time())

        # Check if configuration has changed -> restart
        if self.config_mtime != os.stat(self.paths.config_file).st_mtime:
            os.execv(__file__, sys.argv)

        # Exit on various instances
        if not self.foreground:
            if not os.path.exists(self.paths.pid_file):  # pidfile is missing
                sys.exit(0)
            if (
                time.time() - os.stat(self.paths.pid_file).st_mtime
                > self.settings.heartbeat_timeout
            ):  # heartbeat timeout
                sys.exit(0)
            with open(self.paths.pid_file) as opened_pid_file:
                if os.getpid() != int(opened_pid_file.read()):  # pidfile differs
                    sys.exit(0)

        self.update_watched_folders()
        signal.alarm(self.settings.write_interval)

    def handle_event(self, what, event):
        # type: (str, pyinotify.Event) -> None
        if event.dir:
            return  # Only monitor files

        if len(self.output) > self.settings.max_messages_per_interval:
            last_message = "warning\tMaximum messages reached: %d per %d seconds" % (
                self.settings.max_messages_per_interval,
                self.settings.write_interval,
            )
            if self.output[-1] != last_message:
                self.output.append(last_message)
            return

        path = event.path
        path_config = self.folder_configs.get(path)
        if not path_config:
            return  # shouldn't happen, maybe on subfolders (not supported)

        filename = os.path.basename(event.pathname)
        if what in path_config["monitor_all"] or filename in path_config["monitor_files"].get(
            what, []
        ):
            line = "%d\t%s\t%s" % (time.time(), what, event.pathname)
            self.output.append(line)
            if self.foreground:
                sys.stdout.write("%s\n" % line)

    def update_watched_folders(self):
        # type: () -> None
        for folder, attributes in self.folder_configs.items():
            if attributes.get("watch_descriptor"):
                if not self.watch_manager.get_path(attributes["watch_descriptor"].get(folder)):
                    del attributes["watch_descriptor"]
            elif os.path.exists(folder):
                new_wd = self.watch_manager.add_watch(folder, attributes["mask"], rec=True)
                if new_wd.get(folder) > 0:
                    attributes["watch_descriptor"] = new_wd


# Maps the mode names used in mk_inotify.cfg to the pyinotify mask names
EVENT_MASK_NAMES = {
    "access": "IN_ACCESS",
    "open": "IN_OPEN",
    "create": "IN_CREATE",
    "delete": "IN_DELETE",
    "modify": "IN_MODIFY",
    "movedto": "IN_MOVED_TO",
    "movedfrom": "IN_MOVED_FROM",
    "moveself": "IN_MOVE_SELF",
}


def get_event_masks(inotify_module):
    # type: (object) -> dict[str, int]
    return {mode: getattr(inotify_module, name) for mode, name in EVENT_MASK_NAMES.items()}


def make_event_handler_class(inotify_module):  # type: ignore[explicit-any]
    # type: (Any) -> type
    """Create the event handler class

    Deferred to call time, as pyinotify may not be importable.
    """

    # The suppression below is needed because without an actual pyinotify
    # package available, the superclass is effectively Any.
    class NotifyEventHandler(inotify_module.ProcessEvent):  # type: ignore[misc]
        def my_init(self, monitor):
            # type: (Monitor) -> None
            self.monitor = monitor

        def process_IN_MOVED_TO(self, event):
            # type: (pyinotify.Event) -> None
            self.monitor.handle_event("movedto", event)

        def process_IN_MOVED_FROM(self, event):
            # type: (pyinotify.Event) -> None
            self.monitor.handle_event("movedfrom", event)

        def process_IN_MOVE_SELF(self, event):
            # type: (pyinotify.Event) -> None
            self.monitor.handle_event("moveself", event)

        def process_IN_CREATE(self, event):
            # type: (pyinotify.Event) -> None
            self.monitor.handle_event("create", event)

        def process_IN_DELETE(self, event):
            # type: (pyinotify.Event) -> None
            self.monitor.handle_event("delete", event)

        def process_IN_MODIFY(self, event):
            # type: (pyinotify.Event) -> None
            self.monitor.handle_event("modify", event)

        def process_IN_OPEN(self, event):
            # type: (pyinotify.Event) -> None
            self.monitor.handle_event("open", event)

    return NotifyEventHandler


def compute_folder_configs(config, event_masks):  # type: ignore[explicit-any]
    # type: (configparser.ConfigParser, Mapping[str, int]) -> dict[str, dict[str, Any]]
    folder_configs = {}  # type: dict[str, dict[str, Any]]  # type: ignore[explicit-any]
    for section in config.sections():
        if section == "global":
            continue
        section_tokens = section.split("|")

        folder = section_tokens[0]
        folder_configs.setdefault(
            folder,
            {"add_modes": {}, "del_modes": {}, "all_add_modes": set(), "all_del_modes": set()},
        )

        files = None
        if len(section_tokens) > 1:
            files = set(section_tokens[1:])

        add_modes = set()
        del_modes = set()
        for key, value in config.items(section):
            if key in event_masks:
                if value == "1":
                    add_modes.add(key)
                else:
                    del_modes.add(key)

        if files:
            for mode in add_modes:
                folder_configs[folder]["add_modes"].setdefault(mode, set())
                folder_configs[folder]["add_modes"][mode].update(files)
            for mode in del_modes:
                folder_configs[folder]["del_modes"].setdefault(mode, set())
                folder_configs[folder]["del_modes"][mode].update(files)
        else:
            folder_configs[folder]["all_add_modes"].update(add_modes)
            folder_configs[folder]["all_del_modes"].update(del_modes)

    # Evaluate config
    for folder, attributes in folder_configs.items():
        required_modes = set()
        for mode in attributes["add_modes"]:
            if mode not in attributes["all_del_modes"]:
                required_modes.add(mode)

        files_to_monitor = {}  # type: dict[str, set]
        skip_modes = set()
        for mode in required_modes:
            files_to_monitor.setdefault(mode, set())
            files_to_monitor[mode].update(attributes["add_modes"][mode])
            files_to_monitor[mode] -= attributes["del_modes"].get(mode, set())
            if not files_to_monitor[mode]:
                skip_modes.add(mode)

        attributes["monitor_files"] = files_to_monitor
        attributes["monitor_all"] = attributes["all_add_modes"] - attributes["all_del_modes"]
        attributes["modes"] = required_modes - skip_modes

        # Determine mask
        attributes["mask"] = 0
        for mode in attributes["modes"]:
            attributes["mask"] |= event_masks[mode]
        for mode in attributes["monitor_all"]:
            attributes["mask"] |= event_masks[mode]

    return folder_configs


def main(argv=None):
    # type: (list[str] | None) -> None
    opt_foreground = parse_arguments(sys.argv[1:] if argv is None else argv).foreground
    if pyinotify is None:
        sys.stderr.write("Error: Python plugin pyinotify is not installed\n")
        sys.exit(1)

    paths = get_paths(os.environ)

    config = configparser.ConfigParser({})
    if not os.path.exists(paths.config_file):
        sys.exit(0)
    config_mtime = os.stat(paths.config_file).st_mtime
    config.read(paths.config_file)
    settings = read_global_settings(config)

    if is_other_instance_running(paths.pid_file):
        # Another mk_notify process is already running..
        # Simply output the current statistics and exit
        output_data(paths.vardir, paths.configured_paths, settings.stats_retention, time.time())

        # The pidfile is also the heartbeat file for the running process
        os.utime(paths.pid_file, None)
        sys.exit(0)

    # Reaching this point means that no mk_inotify is currently running
    if not opt_foreground:
        daemonize(paths.pid_file)

    folder_configs = compute_folder_configs(config, get_event_masks(pyinotify))
    monitor = Monitor(
        folder_configs,
        settings,
        paths,
        opt_foreground,
        pyinotify.WatchManager(),
        config_mtime,
    )

    monitor.update_watched_folders()
    if opt_foreground:
        import pprint

        sys.stdout.write(pprint.pformat(folder_configs))

    # In the event that new file permissions need to be set, let's clean up.
    if os.path.exists(paths.configured_paths):
        os.remove(paths.configured_paths)

    # Save monitored file/folder information specified in mk_inotify.cfg
    with open(paths.configured_paths, "w") as opened_conf_paths:
        opened_conf_paths.write("\n".join(get_watched_files(folder_configs)) + "\n")

    # Event handler
    eh = make_event_handler_class(pyinotify)(monitor=monitor)
    notifier = pyinotify.Notifier(monitor.watch_manager, eh)

    # Wake up every few seconds, check heartbeat and write data to disk
    signal.signal(signal.SIGALRM, monitor.wakeup)
    signal.alarm(settings.write_interval)

    notifier.loop()


if __name__ == "__main__":
    main()

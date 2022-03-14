#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Settings handling for the Check_MK event console."""

# For some background about various design decisions below, see the concise
# but excellent article "Parsing Command Line Arguments" in the FPComplete blog
# at https://www.fpcomplete.com/blog/2017/12/parsing-command-line-arguments.

import sys
from argparse import ArgumentParser, ArgumentTypeError, RawDescriptionHelpFormatter
from pathlib import Path
from typing import NamedTuple, Optional, Union


class AnnotatedPath(NamedTuple):
    """a filesystem path with a user-presentable description"""

    description: str
    value: Path


class Paths(NamedTuple):
    """filesystem paths related to the event console"""

    main_config_file: AnnotatedPath
    config_dir: AnnotatedPath
    rule_pack_dir: AnnotatedPath
    mkp_rule_pack_dir: AnnotatedPath
    unix_socket: AnnotatedPath
    event_socket: AnnotatedPath
    event_pipe: AnnotatedPath
    pid_file: AnnotatedPath
    log_file: AnnotatedPath
    history_dir: AnnotatedPath
    messages_dir: AnnotatedPath
    master_config_file: AnnotatedPath
    slave_status_file: AnnotatedPath
    spool_dir: AnnotatedPath
    status_file: AnnotatedPath
    status_server_profile: AnnotatedPath
    event_server_profile: AnnotatedPath
    compiled_mibs_dir: AnnotatedPath
    mongodb_config_file: AnnotatedPath


def _default_paths(omd_root: Path, default_config_dir: Path) -> Paths:
    """Returns all default filesystem paths related to the event console"""
    run_dir = omd_root / "tmp/run/mkeventd"
    state_dir = omd_root / "var/mkeventd"
    return Paths(
        main_config_file=AnnotatedPath("main configuration", default_config_dir / "mkeventd.mk"),
        config_dir=AnnotatedPath("configuration directory", default_config_dir / "mkeventd.d"),
        rule_pack_dir=AnnotatedPath(
            "rule pack directory", default_config_dir / "mkeventd.d" / "wato"
        ),
        mkp_rule_pack_dir=AnnotatedPath(
            "rule pack export directory", default_config_dir / "mkeventd.d" / "mkp" / "rule_packs"
        ),
        unix_socket=AnnotatedPath("Unix socket", run_dir / "status"),
        event_socket=AnnotatedPath("event socket", run_dir / "eventsocket"),
        event_pipe=AnnotatedPath("event pipe", run_dir / "events"),
        pid_file=AnnotatedPath("PID file", run_dir / "pid"),
        log_file=AnnotatedPath("log file", omd_root / "var/log/mkeventd.log"),
        history_dir=AnnotatedPath("history directory", state_dir / "history"),
        messages_dir=AnnotatedPath("messages directory", state_dir / "messages"),
        master_config_file=AnnotatedPath("master configuraion", state_dir / "master_config"),
        slave_status_file=AnnotatedPath("slave status", state_dir / "slave_status"),
        spool_dir=AnnotatedPath("spool directory", state_dir / "spool"),
        status_file=AnnotatedPath("status file", state_dir / "status"),
        status_server_profile=AnnotatedPath(
            "status server profile", state_dir / "StatusServer.profile"
        ),
        event_server_profile=AnnotatedPath(
            "event server profile", state_dir / "EventServer.profile"
        ),
        compiled_mibs_dir=AnnotatedPath(
            "compiled MIBs directory", omd_root / "local/share/check_mk/compiled_mibs"
        ),
        mongodb_config_file=AnnotatedPath("MongoDB configuration", omd_root / "etc/mongodb.conf"),
    )


class PortNumber(NamedTuple):
    """a network port number"""

    value: int


class PortNumbers(NamedTuple):
    """network port numbers related to the event console"""

    syslog_udp: PortNumber
    syslog_tcp: PortNumber
    snmptrap_udp: PortNumber


def _default_port_numbers() -> PortNumbers:
    """Returns all port numbers related to the event console"""
    return PortNumbers(
        syslog_udp=PortNumber(514), syslog_tcp=PortNumber(514), snmptrap_udp=PortNumber(162)
    )


class FileDescriptor(NamedTuple):
    """a Unix file descriptor number"""

    value: int


class ECArgumentParser(ArgumentParser):
    """An argument parser for the event console"""

    def __init__(self, prog: str, version: str, paths: Paths, port_numbers: PortNumbers) -> None:
        super().__init__(
            prog=prog,
            formatter_class=RawDescriptionHelpFormatter,
            description="Start the Check_MK event console.",
            epilog=self._epilog(paths),
        )
        self._add_arguments(version, port_numbers)

    @staticmethod
    def _epilog(paths: Paths) -> str:
        width = max(len(p.description) for p in paths) + 1  # for colon
        return "Paths used by the event console:\n\n" + "\n".join(
            "  {:<{width}} {}".format(p.description + ":", p.value, width=width) for p in paths
        )

    def _add_arguments(self, version: str, port_numbers: PortNumbers) -> None:
        self.add_argument(
            "-V", "--version", action="version", version="%(prog)s version " + version
        )
        self.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity")
        self.add_argument("--syslog", action="store_true", help="enable built-in UDP syslog server")
        self.add_argument(
            "--syslog-fd",
            metavar="FD",
            type=self._file_descriptor,
            help=(
                "use the given file descriptor instead of UDP port %d"
                % port_numbers.syslog_udp.value
            ),
        )
        self.add_argument(
            "--syslog-tcp", action="store_true", help="enable built-in TCP syslog server"
        )
        self.add_argument(
            "--syslog-tcp-fd",
            metavar="FD",
            type=self._file_descriptor,
            help=(
                "use the given file descriptor instead of TCP port %d"
                % port_numbers.syslog_tcp.value
            ),
        )
        self.add_argument("--snmptrap", action="store_true", help="enable built-in snmptrap server")
        self.add_argument(
            "--snmptrap-fd",
            metavar="FD",
            type=self._file_descriptor,
            help=(
                "use the given file descriptor instead of UDP port %d"
                % port_numbers.snmptrap_udp.value
            ),
        )
        self.add_argument(
            "-g",
            "--foreground",
            action="store_true",
            help="run in the foreground instead of daemonizing",
        )
        self.add_argument(
            "-d",
            "--debug",
            action="store_true",
            help="enable debug mode, letting exceptions through",
        )
        self.add_argument(
            "--profile-status",
            action="store_true",
            help="create performance profile for status thread",
        )
        self.add_argument(
            "--profile-event",
            action="store_true",
            help="create performance profile for event thread",
        )

    @staticmethod
    def _file_descriptor(value: str) -> FileDescriptor:
        """A custom argument type for file descriptors, i.e. non-negative integers"""
        try:
            file_desc = int(value)
            if file_desc < 0:
                raise ValueError
        except ValueError:
            raise ArgumentTypeError("invalid file descriptor value: %r" % value)
        return FileDescriptor(file_desc)


# a communication endpoint, e.g. for syslog or SNMP
EndPoint = Union[PortNumber, FileDescriptor]


def _endpoint(
    enabled: bool, file_descriptor: FileDescriptor, default_port_number: PortNumber
) -> Optional[EndPoint]:
    """Returns a communication endpoint based on given commandline arguments"""
    if not enabled:
        return None
    if file_descriptor is None:
        return default_port_number
    return file_descriptor


class Options(NamedTuple):
    """various post-processed commandline options"""

    verbosity: int
    syslog_udp: Optional[EndPoint]
    syslog_tcp: Optional[EndPoint]
    snmptrap_udp: Optional[EndPoint]
    foreground: bool
    debug: bool
    profile_status: bool
    profile_event: bool


class Settings(NamedTuple):
    """all settings of the event console"""

    paths: Paths
    options: Options


def settings(version: str, omd_root: Path, default_config_dir: Path, argv: list[str]) -> Settings:
    """Returns all event console settings"""
    paths = _default_paths(omd_root, default_config_dir)
    port_numbers = _default_port_numbers()
    parser = ECArgumentParser(Path(argv[0]).name, version, paths, port_numbers)
    args = parser.parse_args(argv[1:])
    options = Options(
        verbosity=args.verbose,
        syslog_udp=_endpoint(args.syslog, args.syslog_fd, port_numbers.syslog_udp),
        syslog_tcp=_endpoint(args.syslog_tcp, args.syslog_tcp_fd, port_numbers.syslog_tcp),
        snmptrap_udp=_endpoint(args.snmptrap, args.snmptrap_fd, port_numbers.snmptrap_udp),
        foreground=args.foreground,
        debug=args.debug,
        profile_status=args.profile_status,
        profile_event=args.profile_event,
    )
    return Settings(paths=paths, options=options)


if __name__ == "__main__":
    import cmk.utils.paths
    import cmk.utils.version as cmk_version

    print(
        settings(
            str(cmk_version.__version__),
            cmk.utils.paths.omd_root,
            Path(cmk.utils.paths.default_config_dir),
            sys.argv,
        )
    )

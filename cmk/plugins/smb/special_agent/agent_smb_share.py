#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_smb_share

Checkmk special agent for SMB shares
"""
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import argparse
import logging
import socket
import sys
import traceback
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from datetime import datetime, UTC
from fnmatch import fnmatch
from typing import NamedTuple

from smb.base import NotConnectedError, ProtocolError, SharedFile
from smb.smb_structs import OperationFailure
from smb.SMBConnection import SMBConnection

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option, Secret
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

__version__ = "2.6.0b1"

AGENT = "smb_share"

PASSWORD_OPTION = "password"


class SMBShareAgentError(Exception): ...


class File(NamedTuple):
    path: str
    file: SharedFile

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, File):
            return NotImplemented

        return self.path == other.path

    def __hash__(self) -> int:
        return hash(self.path)


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(
        prog=prog, description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument(
        "--vcrtrace",
        "--tracefile",
        default=False,
        action=vcrtrace(
            # This is the result of a refactoring.
            # I did not check if it makes sense for this special agent.
            filter_headers=[("authorization", "****")],
        ),
    )
    parser.add_argument(
        "hostname",
        type=str,
        metavar="NAME",
        help="Name of the remote host with SMB shares",
    )
    parser.add_argument(
        "ip_address",
        type=str,
        metavar="ADDRESS",
        help="IP address of the remote host",
    )

    parser.add_argument(
        "--username",
        type=str,
        metavar="USERNAME",
        help="User that has rights to access shares",
        default="",
    )
    parser_add_secret_option(
        parser,
        long=f"--{PASSWORD_OPTION}",
        required=False,
        help="Password of user used to connect to the shares",
    )

    parser.add_argument(
        "--patterns",
        type=str,
        nargs="*",
        metavar="PATTERN1 PATTERN2 ...",
        help=(
            "Patterns used to filter which files will be monitored."
            "In case of multiple patterns specified, all patterns will be used."
        ),
        default=[],
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help=("Use recursive pattern search"),
    )
    return parser.parse_args(argv)


def get_child_dirs(conn, share_name, subdir):
    yield subdir

    for shared_file in conn.listPath(share_name, subdir):
        if shared_file.filename in (".", ".."):
            continue

        relative_path = f"{subdir}{shared_file.filename}"
        if shared_file.isDirectory:
            yield from get_child_dirs(conn, share_name, f"{relative_path}\\")


def iter_shared_files(conn, hostname, share_name, pattern, subdir="", recursive=False):
    if pattern[0] == "**" and recursive:
        child_dirs = get_child_dirs(conn, share_name, subdir)
        for child_dir in child_dirs:
            if len(pattern) > 1:
                yield from iter_shared_files(
                    conn, hostname, share_name, pattern[1:], subdir=child_dir, recursive=recursive
                )
                continue

            yield from iter_shared_files(
                conn, hostname, share_name, ["*"], subdir=child_dir, recursive=False
            )
        return

    for shared_file in conn.listPath(share_name, subdir):
        if shared_file.filename in (".", ".."):
            continue

        relative_path = f"{subdir}{shared_file.filename}"
        absolute_path = f"\\\\{hostname}\\{share_name}\\{relative_path}"

        if not fnmatch(shared_file.filename.lower(), pattern[0].lower()):
            continue

        if shared_file.isDirectory and len(pattern) > 1:
            yield from iter_shared_files(
                conn,
                hostname,
                share_name,
                pattern[1:],
                subdir=f"{relative_path}\\",
                recursive=recursive,
            )
            continue

        if not shared_file.isDirectory and len(pattern) == 1:
            yield File(absolute_path, shared_file)


def get_all_shared_files(
    conn: SMBConnection, hostname: str, patterns: list[str], recursive: bool
) -> Generator[tuple[str, set[File]]]:
    share_names = [s.name.lower() for s in conn.listShares()]
    for pattern_string in patterns:
        pattern = pattern_string.strip("\\").split("\\")
        if len(pattern) < 3:
            raise SMBShareAgentError(
                f"Invalid pattern {pattern_string}. Pattern has to consist of host name, share and file matching pattern"
            )

        if pattern[0] != hostname:
            raise SMBShareAgentError(f"Pattern {pattern_string} doesn't match {hostname} host name")

        share_name = pattern[1]
        if share_name.lower() not in share_names:
            raise SMBShareAgentError(f"Share {share_name} doesn't exist on host {hostname}")

        yield (
            pattern_string,
            set(iter_shared_files(conn, hostname, share_name, pattern[2:], recursive=recursive)),
        )


def write_section(all_files: Generator[tuple[str, set[File]]]) -> None:
    now = int(datetime.timestamp(datetime.now(tz=UTC)))
    sys.stdout.write(
        f"<<<fileinfo:sep(124)>>>\n{now}\n[[[header]]]\nname|status|size|time\n[[[content]]]\n"
    )
    for pattern, shared_files in all_files:
        if not shared_files:
            sys.stdout.write(f"{pattern}|missing\n")
            continue

        for shared_file in sorted(shared_files):
            file_obj = shared_file.file
            age = int(file_obj.last_write_time)
            sys.stdout.write(f"{shared_file.path}|ok|{file_obj.file_size}|{age}\n")


@contextmanager
def connect(
    username: str, password: Secret[str], remote_name: str, ip_address: str
) -> Generator[SMBConnection]:
    logging.debug("Creating SMB connection")
    conn = SMBConnection(
        username, password.reveal(), socket.gethostname(), remote_name, is_direct_tcp=True
    )

    try:
        logging.debug("Connecting to %s on port 445", ip_address)
        success = conn.connect(ip_address, 445)
    except (OSError, NotConnectedError):
        raise SMBShareAgentError(
            "Could not connect to the remote host. Check your ip address and remote name."
        )
    except ProtocolError as err:
        raise SMBShareAgentError(
            f"Stack trace:\n{traceback.format_exc()}"
            f"Could not connect to the remote host. Protocol error occurred: {err}."
        )

    if not success:
        raise SMBShareAgentError(
            "Connection to the remote host was declined. Check your credentials."
        )

    logging.debug("Connection successfully established")

    try:
        yield conn
    finally:
        conn.close()


def smb_share_agent(args: argparse.Namespace) -> int:
    try:
        with connect(
            args.username,
            resolve_secret_option(args, PASSWORD_OPTION),
            args.hostname,
            args.ip_address,
        ) as conn:
            all_files = get_all_shared_files(conn, args.hostname, args.patterns, args.recursive)
            logging.debug("Querying share files and writing fileinfo section")
            write_section(all_files)
    except SMBShareAgentError as err:
        sys.stderr.write(str(err))
        return 1
    except OperationFailure as err:
        sys.stderr.write(str(err.args[0]))
        return 1
    logging.debug("Agent finished successfully")
    return 0


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    """Main entry point"""
    return smb_share_agent(parse_arguments(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())

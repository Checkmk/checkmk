#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

from cmk.special_agents.v0_unstable.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser


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


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
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

    parser.add_argument(
        "--password",
        type=str,
        metavar="PASSWORD",
        help="Password of user used to connect to the shares",
        default="",
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
) -> Generator[tuple[str, set[File]], None, None]:
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


def write_section(all_files: Generator[tuple[str, set[File]], None, None]) -> None:
    with SectionWriter("fileinfo", separator="|") as writer:
        now = datetime.now(tz=UTC)
        writer.append(int(datetime.timestamp(now)))
        writer.append("[[[header]]]")
        writer.append("name|status|size|time")
        writer.append("[[[content]]]")
        for pattern, shared_files in all_files:
            if not shared_files:
                writer.append(f"{pattern}|missing")
                continue

            for shared_file in sorted(shared_files):
                file_obj = shared_file.file
                age = int(file_obj.last_write_time)
                file_info = f"{shared_file.path}|ok|{file_obj.file_size}|{age}"
                writer.append(file_info)


@contextmanager
def connect(
    username: str, password: str, remote_name: str, ip_address: str
) -> Generator[SMBConnection, None, None]:
    logging.debug("Creating SMB connection")
    conn = SMBConnection(username, password, socket.gethostname(), remote_name, is_direct_tcp=True)

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


def smb_share_agent(args: Args) -> int:
    try:
        with connect(args.username, args.password, args.hostname, args.ip_address) as conn:
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


def main() -> int:
    """Main entry point"""
    return special_agent_main(parse_arguments, smb_share_agent)

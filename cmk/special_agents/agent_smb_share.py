#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import socket
from contextlib import contextmanager
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Generator, List, NamedTuple, Optional, Sequence, Tuple

from smb.base import NotConnectedError, SharedFile  # type: ignore[import]
from smb.smb_structs import OperationFailure  # type: ignore[import]
from smb.SMBConnection import SMBConnection  # type: ignore[import]

from cmk.special_agents.utils.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser


class File(NamedTuple):
    path: str
    file: SharedFile


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
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
    return parser.parse_args(argv)


def iter_shared_files(
    conn: SMBConnection, hostname: str, share_name: str, pattern: List[str], subdir: str = ""
) -> Generator[File, None, None]:

    for shared_file in conn.listPath(share_name, subdir):
        if shared_file.filename in (".", ".."):
            continue

        relative_path = f"{subdir}{shared_file.filename}"
        absolute_path = f"\\\\{hostname}\\{share_name}\\{relative_path}"

        if not fnmatch(shared_file.filename, pattern[0]):
            continue

        if shared_file.isDirectory and len(pattern) > 1:
            yield from iter_shared_files(
                conn, hostname, share_name, pattern[1:], subdir=f"{relative_path}\\"
            )
            continue

        if not shared_file.isDirectory and len(pattern) == 1:
            yield File(absolute_path, shared_file)


def get_all_shared_files(
    conn: SMBConnection, hostname: str, patterns: List[str]
) -> Generator[Tuple[str, List[File]], None, None]:
    share_names = [s.name for s in conn.listShares()]
    for pattern_string in patterns:
        pattern = pattern_string.strip("\\").split("\\")
        if len(pattern) < 3:
            raise RuntimeError(
                f"Invalid pattern {pattern_string}. Pattern has to consist of hostname, share and file matching pattern"
            )

        if pattern[0] != hostname:
            raise RuntimeError(f"Pattern {pattern_string} doesn't match {hostname} hostname")

        share_name = pattern[1]
        if share_name not in share_names:
            raise RuntimeError(f"Share {share_name} doesn't exist on host {hostname}")

        yield pattern_string, list(iter_shared_files(conn, hostname, share_name, pattern[2:]))


def write_section(all_files: Generator[Tuple[str, List[File]], None, None]) -> None:
    with SectionWriter("fileinfo", separator="|") as writer:
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        writer.append(int(datetime.timestamp(now)))
        writer.append("[[[header]]]")
        writer.append("name|status|size|time")
        writer.append("[[[content]]]")
        for pattern, shared_files in all_files:
            if not shared_files:
                writer.append(f"{pattern}|missing")
                continue

            for shared_file in shared_files:
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
        raise RuntimeError(
            "Could not connect to the remote host. Check your ip address and remote name."
        )

    if not success:
        raise RuntimeError("Connection to the remote host was declined. Check your credentials.")

    logging.debug("Connection successfully established")

    try:
        yield conn
    finally:
        conn.close()


def smb_share_agent(args: Args) -> None:
    with connect(args.username, args.password, args.hostname, args.ip_address) as conn:
        all_files = get_all_shared_files(conn, args.hostname, args.patterns)
        try:
            logging.debug("Querying share files and writing fileinfo section")
            write_section(all_files)
        except OperationFailure as err:
            raise RuntimeError(err.args[0])

    logging.debug("Agent finished successfully")


def main() -> int:
    """Main entry point"""
    special_agent_main(parse_arguments, smb_share_agent)
    return 0

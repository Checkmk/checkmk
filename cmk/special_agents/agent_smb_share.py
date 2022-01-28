#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
        "share_names",
        type=str,
        nargs="*",
        metavar="SHARE1 SHARE2 ...",
        help="Share names from which files are collected",
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
        "--port", type=int, metavar="PORT", help="Port to be used by SMB client", default=139
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
    conn: SMBConnection, share_name: str, pattern: str, subdir: str = ""
) -> Generator[File, None, None]:
    for shared_file in conn.listPath(share_name, subdir):
        if shared_file.filename in (".", ".."):
            continue

        relative_path = f"{subdir}{shared_file.filename}"
        absolute_path = f"\\{share_name}\\{relative_path}"

        if shared_file.isDirectory and pattern.startswith(absolute_path):
            yield from iter_shared_files(conn, share_name, pattern, subdir=f"{relative_path}\\")
            return

        if not shared_file.isDirectory and fnmatch(absolute_path, pattern):
            yield File(absolute_path, shared_file)


def get_all_shared_files(
    conn: SMBConnection, share_names: List[str], patterns: List[str]
) -> Generator[Tuple[str, List[File]], None, None]:
    for pattern in patterns:
        shared_files = [
            file for share in share_names for file in iter_shared_files(conn, share, pattern)
        ]
        yield pattern, shared_files


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
def connect(username, password, remote_name, ip_address, port):
    conn = SMBConnection(username, password, socket.gethostname(), remote_name)

    try:
        success = conn.connect(ip_address, port)
    except (OSError, NotConnectedError):
        raise RuntimeError(
            "Could not connect to the remote host. Check your ip address, port and remote name."
        )

    if not success:
        raise RuntimeError("Connection to the remote host was declined. Check your credentials.")

    try:
        yield conn
    finally:
        conn.close()


def smb_share_agent(args: Args) -> None:
    with connect(args.username, args.password, args.hostname, args.ip_address, args.port) as conn:
        all_files = get_all_shared_files(conn, args.share_names, args.patterns)
        try:
            write_section(all_files)
        except OperationFailure as err:
            raise RuntimeError(err.args[0])


def main() -> int:
    """Main entry point"""
    special_agent_main(parse_arguments, smb_share_agent)
    return 0

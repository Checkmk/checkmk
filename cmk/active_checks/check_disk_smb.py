#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class SMBShareDiskUsageProto(Protocol):
    def __call__(
        self,
        *,
        share: str,
        hostname: str,
        user: str,
        password: str,
        workgroup: str | None = None,
        port: int | None = None,
        ip_address: str | None = None,
        configfile: str | None = None,
    ) -> ErrorResult | SMBShare:
        ...


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check_disk_smb",
        description="""Check SMB Disk plugin for monitoring""",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        metavar="TIMEOUT",
        default=15,
        help="Seconds before connection times out (Default: 15)",
    )
    parser.add_argument(
        "share",
        type=str,
        metavar="SHARE",
        help="Share name to be tested",
    )
    parser.add_argument(
        "-W",
        "--workgroup",
        type=str,
        metavar="WORKGROUP",
        help="Workgroup or Domain used.",
    )
    parser.add_argument(
        "-H",
        "--hostname",
        type=str,
        metavar="HOSTNAME",
        help="NetBIOS name of the server",
    )
    parser.add_argument(
        "-P",
        "--port",
        type=int,
        metavar="PORT",
        help="Port to be used to connect to. Some Windows boxes use 139, others 445.",
    )
    parser.add_argument(
        "--levels",
        type=int,
        nargs=2,
        default=[85, 95],
        metavar=("WARNING", "CRITICAL"),
        help="""Percent of used space at which a warning and critical will be generated (Defaults: 85 and 95).
            Warning percentage should be less than critical.""",
    )
    parser.add_argument(
        "-u",
        "--user",
        type=str,
        default="guest",
        metavar="USER",
        help='Username to log in to server. (Defaults to "guest")',
    )
    parser.add_argument(
        "-p",
        "--password",
        type=str,
        default="",
        metavar="PASSWORD",
        help="Password to log in to server. (Defaults to an empty password)",
    )
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        metavar="IP ADDRESS",
        help="IP-address of HOST (only necessary if HOST is in another network)",
    )
    parser.add_argument(
        "-C",
        "--configfile",
        type=str,
        metavar="CONFIGFILE",
        help="Path to configfile which should be used by smbclient (Defaults to smb.conf of your smb installation)",
    )

    return parser.parse_args(argv)


@dataclass(frozen=True)
class ErrorResult:
    state: int
    summary: str


@dataclass(frozen=True)
class SMBShare:
    mountpoint: str
    total_bytes: int
    available_bytes: int


class _SMBShareDiskUsage:
    def __call__(
        self,
        *,
        share: str,
        hostname: str,
        user: str,
        password: str,
        workgroup: str | None = None,
        port: int | None = None,
        ip_address: str | None = None,
        configfile: str | None = None,
    ) -> ErrorResult | SMBShare:
        return self._analyse_completed_result(
            self._execute_disk_usage_command(
                share=share,
                hostname=hostname,
                user=user,
                password=password,
                workgroup=workgroup if workgroup else None,
                port=port if port else None,
                ip_address=ip_address if ip_address else None,
                configfile=configfile if configfile else None,
            ),
            hostname,
            share,
        )

    @staticmethod
    def _execute_disk_usage_command(
        *,
        share: str,
        hostname: str,
        user: str,
        password: str,
        workgroup: str | None = None,
        port: int | None = None,
        ip_address: str | None = None,
        configfile: str | None = None,
    ) -> str:
        smbclient = shutil.which("smbclient")

        cmd = [
            smbclient if smbclient else "/usr/bin/client",
            "//{}/{}".format(hostname, share),
            "-U",
            "{}%{}".format(user, password),
            "-c",
            "du",
        ]

        if workgroup:
            cmd += ["-W", workgroup]
        if port:
            cmd += ["-p", str(port)]
        if configfile:
            cmd += ["-s", configfile]
        if ip_address:
            cmd += ["-I", ip_address]

        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                encoding="utf8",
                check=True,
            ).stdout

        except subprocess.CalledProcessError as e:
            return e.stderr if e.stderr else e.stdout

    def _analyse_completed_result(
        self, completed_result: str, hostname: str, share: str
    ) -> ErrorResult | SMBShare:
        result_lines = self._cleanup_result(completed_result)

        for line in result_lines:
            disk_usage = re.search(r"\s*(\d*) blocks of size (\d*)\. (\d*) blocks available", line)
            if disk_usage:
                # The line matches the regex
                return self._extract_data_from_matching_line(
                    block_count=int(disk_usage.group(1)),
                    block_size=int(disk_usage.group(2)),
                    available_blocks=int(disk_usage.group(3)),
                    hostname=hostname,
                    share=share,
                )

        # No line matches the regex
        return self._extract_data_from_not_matching_lines(result_lines, hostname, share)

    @staticmethod
    def _cleanup_result(completed_result: str) -> Sequence[str]:
        # Remove \t and split on \n
        result_lines = completed_result.replace("\t", "").splitlines()

        if len(result_lines) == 1:  # If there is an error, there will be only one sentence.
            return result_lines
        return [
            line for line in result_lines[:-1] if line
        ]  # We don't need the last line and empty lines

    @staticmethod
    def _extract_data_from_matching_line(
        *,
        block_count: int,
        block_size: int,
        available_blocks: int,
        hostname: str,
        share: str,
    ) -> SMBShare:
        """
        >>> _SMBShareDiskUsage._extract_data_from_matching_line(block_count=100, block_size=1024, available_blocks=50, hostname="hostname", share="share")
        SMBShare(mountpoint='\\\\\\\\hostname\\\\share', total_bytes=102400, available_bytes=51200)
        """

        return SMBShare(
            mountpoint=f"\\\\{hostname}\\{share}",
            total_bytes=block_size * block_count,
            available_bytes=block_size * available_blocks,
        )

    @staticmethod
    def _extract_data_from_not_matching_lines(
        result_lines: Sequence[str], hostname: str, share: str
    ) -> ErrorResult:
        """
        >>> _SMBShareDiskUsage._extract_data_from_not_matching_lines(["session setup failed: NT_STATUS_LOGON_FAILURE"], "hostname", "share")
        ErrorResult(state=2, summary='Access Denied')
        >>> _SMBShareDiskUsage._extract_data_from_not_matching_lines(["do_connect: Connection to 192.168.0.11 failed (Error NT_STATUS_HOST_UNREACHABLE)"], "hostname", "share")
        ErrorResult(state=2, summary='Connection to 192.168.0.11 failed')
        >>> _SMBShareDiskUsage._extract_data_from_not_matching_lines(["tree connect failed: NT_STATUS_BAD_NETWORK_NAME"], "hostname", "share")
        ErrorResult(state=2, summary='Invalid share name \\\\\\\\hostname\\\\share')
        >>> _SMBShareDiskUsage._extract_data_from_not_matching_lines(["some other error"], "hostname", "share")
        ErrorResult(state=3, summary='Result from smbclient not suitable')
        """
        # Default case
        state, summary = 3, "Result from smbclient not suitable"

        for line in result_lines:
            # access denied or logon failure
            if re.search(r"(Access denied|NT_STATUS_LOGON_FAILURE|NT_STATUS_ACCESS_DENIED)", line):
                return ErrorResult(2, "Access Denied")

            # unknown host or connection failure
            if (error := re.search(r"(Unknown host \w*|Connection.*failed)", line)) is not None:
                return ErrorResult(2, error.group(0))

            # invalid share name
            if re.search(r"(You specified an invalid share name|NT_STATUS_BAD_NETWORK_NAME)", line):
                return ErrorResult(2, f"Invalid share name \\\\{hostname}\\{share}")

        return ErrorResult(state, summary)

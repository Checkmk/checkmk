#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Sequence
from pathlib import Path


@dataclasses.dataclass(frozen=True, kw_only=True)
class ServerConfig:
    unix_socket: Path
    pid_file: Path
    access_log: Path
    error_log: Path
    num_workers: int


def server_config(*, run_directory: Path, log_directory: Path) -> ServerConfig:
    return ServerConfig(
        unix_socket=run_directory / "automation-helper.sock",
        pid_file=run_directory / "automation-helper.pid",
        access_log=log_directory / "access.log",
        error_log=log_directory / "error.log",
        num_workers=1,
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Schedule:
    path: Path
    ignore_directories: bool
    recursive: bool
    patterns: Sequence[str] | None = None


def watcher_schedules(omd_root: Path) -> list[Schedule]:
    return [
        Schedule(
            ignore_directories=True,
            recursive=False,
            path=omd_root / "etc" / "check_mk",
            patterns=["main.mk", "local.mk", "final.mk", "experimental.mk"],
        ),
        Schedule(
            path=omd_root / "etc" / "check_mk" / "conf.d",
            ignore_directories=True,
            recursive=True,
            patterns=["*.mk", "*.pkl"],
        ),
        Schedule(
            path=omd_root / "var" / "check_mk" / "autochecks",
            ignore_directories=True,
            recursive=True,
            patterns=["*.mk"],
        ),
        Schedule(
            path=omd_root / "var" / "check_mk" / "discovered_host_labels",
            ignore_directories=True,
            recursive=True,
            patterns=["*.mk"],
        ),
        Schedule(
            path=omd_root / "var" / "check_mk",
            ignore_directories=True,
            recursive=False,
            patterns=["stored_passwords"],
        ),
    ]


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReloaderConfig:
    poll_interval: float
    aggregation_interval: float


def reloader_config() -> ReloaderConfig:
    return ReloaderConfig(
        poll_interval=1.0,
        aggregation_interval=5.0,
    )

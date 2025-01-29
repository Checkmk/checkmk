#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

RELATIVE_CONFIG_PATH_FOR_TESTING = "automation_helper_config.json"


class ServerConfig(BaseModel, frozen=True):
    unix_socket: Path
    pid_file: Path
    access_log: Path
    error_log: Path
    num_workers: int


class Schedule(BaseModel, frozen=True):
    path: Path
    ignore_directories: bool
    recursive: bool
    patterns: Sequence[str] | None = None


class WatcherConfig(BaseModel, frozen=True):
    schedules: Sequence[Schedule]


class ReloaderConfig(BaseModel, frozen=True):
    active: bool  # for testing purposes
    poll_interval: float
    cooldown_interval: float


class Config(BaseModel, frozen=True):
    server_config: ServerConfig
    watcher_config: WatcherConfig
    reloader_config: ReloaderConfig


def default_config(
    *,
    omd_root: Path,
    run_directory: Path,
    log_directory: Path,
) -> Config:
    return Config(
        server_config=ServerConfig(
            unix_socket=run_directory / "automation-helper.sock",
            pid_file=run_directory / "automation-helper.pid",
            access_log=log_directory / "access.log",
            error_log=log_directory / "error.log",
            num_workers=2,
        ),
        watcher_config=WatcherConfig(
            schedules=[
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
        ),
        reloader_config=ReloaderConfig(
            active=True,
            poll_interval=1.0,
            cooldown_interval=5.0,
        ),
    )


def config_from_disk_or_default_config(
    *,
    omd_root: Path,
    run_directory: Path,
    log_directory: Path,
) -> Config:
    return (
        Config.model_validate_json(test_config_path.read_text())
        if (test_config_path := omd_root / RELATIVE_CONFIG_PATH_FOR_TESTING).exists()
        else default_config(
            omd_root=omd_root,
            run_directory=run_directory,
            log_directory=log_directory,
        )
    )

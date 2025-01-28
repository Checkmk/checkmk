#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from pydantic import BaseModel


class ServerConfig(BaseModel, frozen=True):
    unix_socket: Path
    access_log: Path
    error_log: Path


def default_config(omd_root: Path, run_path: Path, log_path: Path) -> ServerConfig:
    return ServerConfig(
        unix_socket=run_path / "ui-job-scheduler.sock",
        access_log=log_path / "access.log",
        error_log=log_path / "error.log",
    )

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from pydantic import BaseModel

from cmk.ccc.store import load_mk_file


class Config(BaseModel, frozen=True):
    max_file_age: int | None = None
    min_free_bytes: tuple[int, int] | None = None
    cleanup_abandoned_host_files: int | None = None


DEFAULT_CONFIG = Config(cleanup_abandoned_host_files=2592000)


def read_config(path: Path) -> Config:
    class _Config(BaseModel, frozen=True):
        diskspace_cleanup: Config

    raw_config = load_mk_file(
        path / "sitespecific.mk",
        default=load_mk_file(
            path / "global.mk", default=DEFAULT_CONFIG.model_dump(exclude_none=True), lock=False
        ),
        lock=False,
    )
    if "diskspace_cleanup" not in raw_config:
        return DEFAULT_CONFIG
    return _Config.model_validate(raw_config).diskspace_cleanup

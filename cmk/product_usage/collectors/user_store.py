#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

from cmk.ccc import store


def load_users(default_config_dir: Path) -> Mapping[str, Mapping[str, object]]:
    """The users in the GUI's user store, by user ID"""
    users: Mapping[str, Mapping[str, object]] = store.load_from_mk_file(
        default_config_dir / "multisite.d/wato/users.mk",
        key="multisite_users",
        default={},
        lock=False,
    )
    return users

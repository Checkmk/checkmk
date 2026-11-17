#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

from cmk.ccc import store


def write_user_store(default_config_dir: Path, users: Mapping[str, Mapping[str, object]]) -> None:
    """Write the users in the format of the GUI's user store"""
    path = default_config_dir / "multisite.d/wato/users.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    store.save_to_mk_file(path, key="multisite_users", value=users)

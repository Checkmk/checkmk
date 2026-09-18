#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path

from cmk.ccc.user import UserId


def user_directories(profile_dir: Path) -> Iterator[Path]:
    # A missing or unreadable profile directory means there is nothing to work on.
    with suppress(OSError):
        for entry in profile_dir.iterdir():
            try:
                UserId(entry.name)
            except ValueError:
                continue  # files such as ldap_*_sync_time.mk live here, too
            # Not is_dir(): a symlink named like a user would lead the sweep out of
            # the profile directory.
            if entry.is_dir(follow_symlinks=False):
                yield entry

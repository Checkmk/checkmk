#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from cmk.ccc import store
from cmk.product_usage.schema import Session


def collect(var_dir: Path) -> list[Session]:
    """The stored sessions of all users, as the GUI's session store has them"""
    sessions = [
        session
        for path in (var_dir / "web").glob("*/session_info.mk")
        for session in _read_sessions(path)
    ]
    return sorted(sessions, key=lambda s: (s.started_at, s.last_activity))


def _read_sessions(path: Path) -> list[Session]:
    # Locking creates the file empty before the GUI writes the user's first session to it
    if not (text := store.load_text_from_file(path)):
        return []
    return [
        Session(
            started_at=session_info["started_at"],
            last_activity=session_info["last_activity"],
        )
        for session_info in ast.literal_eval(text).values()
    ]

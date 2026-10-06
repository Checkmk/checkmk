#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The SQLite `Backend`."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from sqlite3 import Connection
from typing import override

from cmk.schema_manager._paths import db_path
from cmk.schema_manager.backend.base import Backend
from cmk.schema_manager.revision import RevisionChain


@dataclass(frozen=True)
class Sqlite(Backend[Connection]):
    """SQLite-backed databases, one file per database name.

    A name's file is `var/check_mk/<name>/db.sqlite3`, resolved on every
    call, so nothing depends on the environment at construction time.
    """

    configure: Callable[[Connection], None] = lambda _: None

    def path(self, name: str) -> Path:
        return db_path(name)

    @override
    def connect(self, name: str, *, create: bool = False) -> AbstractContextManager[Connection]:
        raise NotImplementedError("implemented by CMK-40103")

    @override
    def exists(self, name: str) -> bool:
        return self.path(name).exists()

    @override
    def apply_pending(
        self, context: Connection, chain: RevisionChain[Connection], logger: Logger
    ) -> None:
        raise NotImplementedError("implemented by CMK-40103")

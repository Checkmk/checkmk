#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import auto, Enum

from cmk.utils.structured_data import SDKey, SDPath


class TreeSource(Enum):
    node = auto()
    table = auto()
    attributes = auto()


@dataclass(frozen=True)
class InventoryPath:
    path: SDPath
    source: TreeSource
    key: SDKey | None = None

    @classmethod
    def parse(cls, raw_path: str) -> InventoryPath:
        if not raw_path:
            return InventoryPath(
                path=tuple(),
                source=TreeSource.node,
            )

        if raw_path.endswith("."):
            path = raw_path[:-1].strip(".").split(".")
            return InventoryPath(
                path=cls._sanitize_path(raw_path[:-1].strip(".").split(".")),
                source=TreeSource.node,
            )

        if raw_path.endswith(":"):
            return InventoryPath(
                path=cls._sanitize_path(raw_path[:-1].strip(".").split(".")),
                source=TreeSource.table,
            )

        path = raw_path.strip(".").split(".")
        sanitized_path = cls._sanitize_path(path[:-1])
        if ":" in path[-2]:
            source = TreeSource.table
            # Forget the last '*' or an index like '17'
            # because it's related to columns (not nodes)
            sanitized_path = sanitized_path[:-1]
        else:
            source = TreeSource.attributes

        return InventoryPath(
            path=sanitized_path,
            source=source,
            key=path[-1],
        )

    @staticmethod
    def _sanitize_path(path: Sequence[str]) -> SDPath:
        # ":": Nested tables, see also lib/structured_data.py
        return tuple(p for part in path for p in (part.split(":") if ":" in part else [part]) if p)

    @property
    def node_name(self) -> str:
        return self.path[-1] if self.path else ""

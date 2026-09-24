#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from enum import auto, Enum

from .trees import SDKey, SDNodeName, SDPath


class TreeSource(Enum):
    node = auto()
    table = auto()
    attributes = auto()


@dataclass(frozen=True)
class InventoryPath:
    path: SDPath
    source: TreeSource
    key: SDKey = SDKey("")

    @property
    def node_name(self) -> str:
        return self.path[-1] if self.path else ""


def _sanitize_path(path: Sequence[str]) -> SDPath:
    return tuple(
        SDNodeName(p) for part in path for p in (part.split(":") if ":" in part else [part]) if p
    )


def parse_internal_raw_path(raw: str) -> InventoryPath:
    if not raw:
        return InventoryPath(
            path=(),
            source=TreeSource.node,
        )
    if raw.endswith("."):
        return InventoryPath(
            path=_sanitize_path(raw[:-1].strip(".").split(".")),
            source=TreeSource.node,
        )
    if raw.endswith(":"):
        return InventoryPath(
            path=_sanitize_path(raw[:-1].strip(".").split(".")),
            source=TreeSource.table,
        )
    path = raw.strip(".").split(".")
    sanitized_path = _sanitize_path(path[:-1])
    if ":" in path[-2]:
        source = TreeSource.table
        sanitized_path = sanitized_path[:-1]
    else:
        source = TreeSource.attributes
    return InventoryPath(
        path=sanitized_path,
        source=source,
        key=SDKey(path[-1]),
    )

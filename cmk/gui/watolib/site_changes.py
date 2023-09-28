#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from typing import Any

from livestatus import SiteId

from cmk.gui.watolib.appendstore import ABCAppendStore
from cmk.gui.watolib.objref import ObjectRef
from cmk.gui.watolib.paths import wato_var_dir

ChangeSpec = dict[str, Any]


class SiteChanges(ABCAppendStore[ChangeSpec]):
    """Manage persisted changes of a single site"""

    def __init__(self, site_id: SiteId) -> None:
        super().__init__(wato_var_dir() / (f"replication_changes_{site_id}.mk"))

    @staticmethod
    def _serialize(entry: ChangeSpec) -> object:
        raw = entry.copy()
        raw["object"] = raw["object"].serialize() if raw["object"] else None
        return raw

    @staticmethod
    def _deserialize(raw: object) -> ChangeSpec:
        if not isinstance(raw, dict):
            raise ValueError("expected a dictionary")
        raw["object"] = ObjectRef.deserialize(raw["object"]) if raw["object"] else None
        return raw

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)

    @staticmethod
    def to_json(entries: Sequence[ChangeSpec]) -> str:
        return json.dumps([SiteChanges._serialize(entry) for entry in entries])

    @staticmethod
    def from_json(raw: str) -> Sequence[ChangeSpec]:
        return [SiteChanges._deserialize(entry) for entry in json.loads(raw)]

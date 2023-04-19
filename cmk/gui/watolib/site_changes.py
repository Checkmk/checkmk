#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from livestatus import SiteId

from cmk.gui.watolib.appendstore import ABCAppendStore
from cmk.gui.watolib.objref import ObjectRef, ObjectRefType
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
        # TODO: Parse raw's entries, too, below we have our traditional 'wishful typing'... :-P
        if isinstance(raw["object"], tuple):
            # Migrate the pre 2.0 change entries (Two element tuple: ("Folder/Host", "ident"))
            type_name, ident = raw["object"]
            if type_name in ("CMEHost", "CREHost"):
                type_name = "Host"
            elif type_name in ("CMEFolder", "CREFolder"):
                type_name = "Folder"
            raw["object"] = ObjectRef(ObjectRefType(type_name), ident)
        else:
            raw["object"] = ObjectRef.deserialize(raw["object"]) if raw["object"] else None
        return raw

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)

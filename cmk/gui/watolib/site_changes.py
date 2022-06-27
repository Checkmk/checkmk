#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any, Dict

from cmk.gui.watolib.appendstore import ABCAppendStore
from cmk.gui.watolib.objref import ObjectRef, ObjectRefType
from cmk.gui.watolib.paths import wato_var_dir

ChangeSpec = Dict[str, Any]


class SiteChanges(ABCAppendStore[ChangeSpec]):
    """Manage persisted changes of a single site"""

    @staticmethod
    def make_path(*args: str) -> Path:
        return wato_var_dir() / ("replication_changes_%s.mk" % args[0])

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

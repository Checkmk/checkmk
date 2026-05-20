#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, cast, NotRequired, TypedDict

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.watolib.appendstore import ABCAppendStore
from cmk.gui.watolib.objref import ObjectRef
from cmk.gui.watolib.paths import wato_var_dir


class ChangeSpec(TypedDict):
    id: str
    action_name: str
    text: str
    object: ObjectRef | None
    user_id: UserId | None
    domains: Sequence[str]
    time: float
    # Legacy fields written by ``add_change``; not produced by
    # ``PendingChanges``. Removed in the follow-up commit that reroutes
    # ``add_change`` through ``PendingChanges``; an update-config action
    # rewrites stored records to the new schema before that.
    need_sync: NotRequired[bool]
    need_restart: NotRequired[bool]
    has_been_activated: NotRequired[bool]
    # New fields written by ``PendingChanges``; not produced by the legacy
    # ``add_change`` shim. ``NotRequired`` only while the legacy producer
    # still exists; the follow-up commit tightens these to ``Required``.
    force_sync: NotRequired[bool | None]
    force_restart: NotRequired[bool | None]
    force_apache_reload: NotRequired[bool]
    # Values are ``cmk.gui.watolib.config_domain_name.SerializedSettings``;
    # the loose annotation avoids an import cycle.
    domain_settings: Mapping[str, Any]
    prevent_discard_changes: bool
    diff_text: str | None
    # Added in-memory by ``ActivateChanges.load``; never persisted.
    affected_sites: NotRequired[list[SiteId]]


class SiteChanges(ABCAppendStore[ChangeSpec]):
    """Manage persisted changes of a single site"""

    def __init__(self, site_id: SiteId) -> None:
        super().__init__(wato_var_dir() / (f"replication_changes_{site_id}.mk"))

    @staticmethod
    def _serialize(entry: ChangeSpec) -> object:
        raw: dict[str, object] = dict(entry)
        raw["object"] = entry["object"].serialize() if entry["object"] else None
        return raw

    @staticmethod
    def _deserialize(raw: object) -> ChangeSpec:
        if not isinstance(raw, dict):
            raise ValueError("expected a dictionary")
        raw["object"] = ObjectRef.deserialize(raw["object"]) if raw["object"] else None
        return cast(ChangeSpec, raw)

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)

    @staticmethod
    def to_json(entries: Sequence[ChangeSpec]) -> str:
        return json.dumps([SiteChanges._serialize(entry) for entry in entries])

    @staticmethod
    def from_json(raw: str) -> Sequence[ChangeSpec]:
        return [SiteChanges._deserialize(entry) for entry in json.loads(raw)]

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from typing import NamedTuple

from cmk.utils.type_defs import UserId

import cmk.gui.watolib.git
from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.watolib.appendstore import ABCAppendStore
from cmk.gui.watolib.objref import ObjectRef
from cmk.gui.watolib.paths import wato_var_dir

LogMessage = str | HTML | LazyString


class AuditLogStore(ABCAppendStore["AuditLogStore.Entry"]):
    def __init__(self) -> None:
        super().__init__(wato_var_dir() / "log" / "wato_audit.log")

    class Entry(NamedTuple):
        time: int
        object_ref: ObjectRef | None
        user_id: str
        action: str
        text: LogMessage
        diff_text: str | None

    @staticmethod
    def _serialize(entry: AuditLogStore.Entry) -> object:
        raw = entry._asdict()
        raw["text"] = (
            ("html", str(entry.text)) if isinstance(entry.text, HTML) else ("str", entry.text)
        )
        raw["object_ref"] = raw["object_ref"].serialize() if raw["object_ref"] else None
        return raw

    @staticmethod
    def _deserialize(raw: object) -> AuditLogStore.Entry:
        if not isinstance(raw, dict):
            raise ValueError("expected a dictionary")
        # TODO: Parse raw's entries, too, below we have our traditional 'wishful typing'... :-P
        raw["text"] = HTML(raw["text"][1]) if raw["text"][0] == "html" else raw["text"][1]
        raw["object_ref"] = ObjectRef.deserialize(raw["object_ref"]) if raw["object_ref"] else None
        return AuditLogStore.Entry(**raw)

    def clear(self) -> None:
        """Instead of just removing, like ABCAppendStore, archive the existing file"""
        if not self.exists():
            return

        newpath = self._path.with_name(self._path.name + time.strftime(".%Y-%m-%d"))
        if newpath.exists():
            n = 1
            while True:
                n += 1
                with_num = newpath.with_name(newpath.name + "-%d" % n)
                if not with_num.exists():
                    newpath = with_num
                    break

        self._path.rename(newpath)

    def get_entries_since(self, timestamp: int) -> Sequence[AuditLogStore.Entry]:
        return [entry for entry in self.read() if entry.time > timestamp]

    @classmethod
    def to_json(cls, entries: Sequence[AuditLogStore.Entry]) -> str:
        return json.dumps([cls._serialize(entry) for entry in entries])

    @classmethod
    def from_json(cls, raw: str) -> Sequence[AuditLogStore.Entry]:
        return [cls._deserialize(entry) for entry in json.loads(raw)]


def log_audit(
    action: str,
    message: LogMessage,
    object_ref: ObjectRef | None = None,
    user_id: UserId | None = None,
    diff_text: str | None = None,
) -> None:
    if isinstance(message, LazyString):
        message = message.unlocalized_str()

    if active_config.wato_use_git:
        if isinstance(message, HTML):
            message = escaping.strip_tags(message.value)
        cmk.gui.watolib.git.add_message(message)

    _log_entry(action, message, object_ref, user_id, diff_text)


def _log_entry(
    action: str,
    message: HTML | str,
    object_ref: ObjectRef | None,
    user_id: UserId | None,
    diff_text: str | None,
) -> None:
    entry = AuditLogStore.Entry(
        time=int(time.time()),
        object_ref=object_ref,
        user_id=str(user_id or user.id or "-"),
        action=action,
        text=message,
        diff_text=diff_text,
    )
    AuditLogStore().append(entry)

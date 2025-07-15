#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import copy
import json
import re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple, TypedDict

from cmk.ccc.user import UserId

import cmk.gui.watolib.git
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.watolib.appendstore import ABCAppendStore
from cmk.gui.watolib.objref import ObjectRef
from cmk.gui.watolib.paths import wato_var_dir

LogMessage = str | HTML | LazyString


class AuditLogFilter(TypedDict, total=False):
    timestamp_from: int
    timestamp_to: int
    object_type: str
    object_ident: str
    user_id: str
    filter_regex: str


class AuditLogFilterRaw(TypedDict, total=False):
    timestamp_from: int
    timestamp_to: int
    object_type: str | None
    object_ident: str | None
    user_id: str | None
    filter_regex: str | None


class AuditLogStore(ABCAppendStore["AuditLogStore.Entry"]):
    separator = b"\n"

    def __init__(self, filepath: Path = wato_var_dir() / "log" / "wato_audit.log") -> None:
        super().__init__(path=filepath)

    class Entry(NamedTuple):
        time: int
        object_ref: ObjectRef | None
        user_id: str
        action: str
        text: LogMessage
        diff_text: str | None

        @staticmethod
        def deserialize(raw_entry: object) -> AuditLogStore.Entry:
            raw: object = copy.copy(raw_entry)
            if not isinstance(raw, dict):
                raise ValueError("expected a dictionary")
            # TODO: Parse raw's entries, too, below we have our traditional 'wishful typing'... :-P
            raw["text"] = (
                HTML.without_escaping(raw["text"][1])
                if raw["text"][0] == "html"
                else raw["text"][1]
            )
            raw["object_ref"] = (
                ObjectRef.deserialize(raw["object_ref"]) if raw["object_ref"] else None
            )
            return AuditLogStore.Entry(**raw)

        @staticmethod
        def serialize(entry: AuditLogStore.Entry) -> dict[str, Any]:
            raw = entry._asdict()
            raw["text"] = (
                ("html", str(entry.text)) if isinstance(entry.text, HTML) else ("str", entry.text)
            )
            raw["object_ref"] = raw["object_ref"].serialize() if raw["object_ref"] else None
            return raw

    @staticmethod
    def _serialize(entry: AuditLogStore.Entry) -> object:
        return AuditLogStore.Entry.serialize(entry)

    @staticmethod
    def _deserialize(raw: object) -> AuditLogStore.Entry:
        return AuditLogStore.Entry.deserialize(raw)

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

    def read(self, options: AuditLogFilter | None = None) -> Sequence[AuditLogStore.Entry]:
        entries = super().read()

        if options is None:
            return entries

        return [entry for entry in entries if AuditLogStore.filter_entry(entry, options)]

    @staticmethod
    def filter_entry(entry: AuditLogStore.Entry, options: AuditLogFilter) -> bool:
        if "timestamp_from" in options and entry.time < options["timestamp_from"]:
            return False

        if "timestamp_to" in options and entry.time > options["timestamp_to"]:
            return False

        if "object_type" in options and options["object_type"] != "All":
            if entry.object_ref is None and options["object_type"] != "None":
                return False
            if entry.object_ref and entry.object_ref.object_type.name != options["object_type"]:
                return False

        if "object_ident" in options:
            if entry.object_ref is None and options["object_ident"] != "":
                return False
            if entry.object_ref and entry.object_ref.ident != options["object_ident"]:
                return False

        if "user_id" in options and options["user_id"] is not None:
            if entry.user_id != options["user_id"]:
                return False

        filter_regex: str | None = options["filter_regex"] if "filter_regex" in options else None
        if filter_regex:
            return any(
                re.search(filter_regex, val)
                for val in [entry.user_id, entry.action, str(entry.text)]
            )

        return True

    def get_entries_since(self, timestamp: int) -> Sequence[AuditLogStore.Entry]:
        return [entry for entry in self.read() if entry.time > timestamp]

    @classmethod
    def to_json(cls, entries: Sequence[AuditLogStore.Entry]) -> str:
        return json.dumps([cls._serialize(entry) for entry in entries])

    @classmethod
    def from_json(cls, raw: str) -> Sequence[AuditLogStore.Entry]:
        return [AuditLogStore.Entry.deserialize(entry) for entry in json.loads(raw)]


def log_audit(
    *,
    action: str,
    message: LogMessage,
    user_id: UserId | None,
    use_git: bool,
    object_ref: ObjectRef | None = None,
    diff_text: str | None = None,
) -> None:
    if isinstance(message, LazyString):
        message = message.unlocalized_str()

    if use_git:
        if isinstance(message, HTML):
            message = escaping.strip_tags(str(message))
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
        user_id=str(user_id) if user_id else "-",
        action=action,
        text=message,
        diff_text=diff_text,
    )
    AuditLogStore().append(entry)


def build_audit_log_filter(options: AuditLogFilterRaw) -> AuditLogFilter:
    result = AuditLogFilter()
    if timestamp_from := options.get("timestamp_from"):
        result["timestamp_from"] = timestamp_from
    if timestamp_to := options.get("timestamp_to"):
        result["timestamp_to"] = timestamp_to
    if object_ident := options.get("object_ident", ""):
        result["object_ident"] = object_ident
    if (user_id := options.get("user_id")) is not None:
        result["user_id"] = user_id
    if filter_regex := options.get("filter_regex", ""):
        result["filter_regex"] = filter_regex
    if (object_type := options.get("object_type")) is None:
        result["object_type"] = "None"
    elif object_type == "":
        result["object_type"] = "All"
    else:
        result["object_type"] = object_type
    return result

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path
from typing import NamedTuple, Optional, Union

from cmk.utils.type_defs import UserId

import cmk.gui.watolib.git
from cmk.gui.config import active_config
from cmk.gui.htmllib import HTML
from cmk.gui.logged_in import user
from cmk.gui.utils import escaping
from cmk.gui.watolib.appendstore import ABCAppendStore
from cmk.gui.watolib.objref import ObjectRef
from cmk.gui.watolib.paths import wato_var_dir

LogMessage = Union[str, HTML]


class AuditLogStore(ABCAppendStore["AuditLogStore.Entry"]):
    class Entry(NamedTuple):
        time: int
        object_ref: Optional[ObjectRef]
        user_id: str
        action: str
        text: LogMessage
        diff_text: Optional[str]

    @staticmethod
    def make_path(*args: str) -> Path:
        return wato_var_dir() / "log" / "wato_audit.log"

    @staticmethod
    def _serialize(entry: "AuditLogStore.Entry") -> object:
        raw = entry._asdict()
        raw["text"] = (
            ("html", str(entry.text)) if isinstance(entry.text, HTML) else ("str", entry.text)
        )
        raw["object_ref"] = raw["object_ref"].serialize() if raw["object_ref"] else None
        return raw

    @staticmethod
    def _deserialize(raw: object) -> "AuditLogStore.Entry":
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


def log_audit(
    action: str,
    message: LogMessage,
    object_ref: Optional[ObjectRef] = None,
    user_id: Optional[UserId] = None,
    diff_text: Optional[str] = None,
) -> None:
    if active_config.wato_use_git:
        if isinstance(message, HTML):
            message = escaping.strip_tags(message.value)
        cmk.gui.watolib.git.add_message(message)

    _log_entry(action, message, object_ref, user_id, diff_text)


def _log_entry(
    action: str,
    message: Union[HTML, str],
    object_ref: Optional[ObjectRef],
    user_id: Optional[UserId],
    diff_text: Optional[str],
) -> None:
    entry = AuditLogStore.Entry(
        time=int(time.time()),
        object_ref=object_ref,
        user_id=str(user_id or user.id or "-"),
        action=action,
        text=message,
        diff_text=diff_text,
    )
    AuditLogStore(AuditLogStore.make_path()).append(entry)

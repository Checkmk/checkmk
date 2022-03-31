#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Functions for logging changes and keeping the "Activate Changes" state and finally activating changes."""

import abc
import ast
import enum
import errno
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Type,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from livestatus import SiteId

import cmk.utils
import cmk.utils.store as store
from cmk.utils.object_diff import make_object_diff
from cmk.utils.type_defs import Labels, UserId

import cmk.gui.utils
import cmk.gui.watolib.git
import cmk.gui.watolib.sidebar_reload
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.globals import config, request
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.plugins.watolib.utils import ABCConfigDomain, config_domain_registry, DomainSettings
from cmk.gui.sites import activation_sites, site_is_local
from cmk.gui.utils import escaping
from cmk.gui.utils.logged_in import user
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.watolib import search

if TYPE_CHECKING:
    from cmk.gui.watolib.hosts_and_folders import CREHost

ChangeSpec = Dict[str, Any]
LogMessage = Union[str, HTML]

_VT = TypeVar("_VT")


class ObjectRefType(enum.Enum):
    """Known types of objects"""

    Folder = "Folder"
    Host = "Host"
    User = "User"
    Rule = "Rule"
    Ruleset = "Ruleset"


@dataclass
class ObjectRef:
    """Persisted in audit log and site changes to reference a Checkmk configuration object"""

    object_type: ObjectRefType
    ident: str
    labels: Labels = field(default_factory=dict)

    def serialize(self):
        serialized: Dict[str, Any] = {
            "object_type": self.object_type.name,
            "ident": self.ident,
        }
        if self.labels:
            serialized["labels"] = self.labels
        return serialized

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "ObjectRef":
        return cls(
            object_type=ObjectRefType(serialized["object_type"]),
            ident=serialized["ident"],
            labels=serialized.get("labels", {}),
        )


class ABCAppendStore(Generic[_VT], abc.ABC):
    """Managing a file with structured data that can be appended in a cheap way

    The file holds basic python structures separated by "\0".
    """

    @staticmethod
    @abc.abstractmethod
    def make_path(*args: str) -> Path:
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def _serialize(entry: _VT) -> object:
        """Prepare _VT objects for serialization

        Override this to execute some logic before repr()"""
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def _deserialize(raw: object) -> _VT:
        """Create _VT objects from serialized data

        Override this to execute some logic after literal_eval() to produce _VT objects"""
        raise NotImplementedError()

    def __init__(self, path: Path) -> None:
        self._path = path

    def exists(self) -> bool:
        return self._path.exists()

    # TODO: Implement this locking as context manager
    def read(self, lock: bool = False) -> List[_VT]:
        """Parse the file and return the entries"""
        path = self._path

        if lock:
            store.aquire_lock(path)

        entries = []
        try:
            with path.open("rb") as f:
                for entry in f.read().split(b"\0"):
                    if entry:
                        entries.append(self._deserialize(ast.literal_eval(entry.decode("utf-8"))))
        except IOError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise
        except Exception:
            if lock:
                store.release_lock(path)
            raise

        return entries

    def write(self, entries: List[_VT]) -> None:
        # First truncate the file
        with self._path.open("wb"):
            pass

        for entry in entries:
            self.append(entry)

    def append(self, entry: _VT) -> None:
        path = self._path
        try:
            store.aquire_lock(path)

            with path.open("ab+") as f:
                f.write(repr(self._serialize(entry)).encode("utf-8") + b"\0")
                f.flush()
                os.fsync(f.fileno())

            path.chmod(0o660)

        except Exception as e:
            raise MKGeneralException(_('Cannot write file "%s": %s') % (path, e))

        finally:
            store.release_lock(path)

    def clear(self) -> None:
        try:
            self._path.unlink()
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass  # Not existant -> OK
            else:
                raise


def _wato_var_dir() -> Path:
    return Path(cmk.utils.paths.var_dir, "wato")


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
        return _wato_var_dir() / "log" / "wato_audit.log"

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


def log_audit(
    action: str,
    message: LogMessage,
    object_ref: Optional[ObjectRef] = None,
    user_id: Optional[UserId] = None,
    diff_text: Optional[str] = None,
) -> None:

    if config.wato_use_git:
        if isinstance(message, HTML):
            message = escaping.strip_tags(message.value)
        cmk.gui.watolib.git.add_message(message)

    _log_entry(action, message, object_ref, user_id, diff_text)


def make_diff_text(old_object: Any, new_object: Any) -> Optional[str]:
    if old_object is not None and new_object is not None:
        return make_object_diff(old_object, new_object)
    return None


def add_change(
    action_name: str,
    text: LogMessage,
    object_ref: Optional[ObjectRef] = None,
    diff_text: Optional[str] = None,
    add_user: bool = True,
    need_sync: Optional[bool] = None,
    need_restart: Optional[bool] = None,
    domains: Optional[List[Type[ABCConfigDomain]]] = None,
    sites: Optional[List[SiteId]] = None,
    domain_settings: Optional[DomainSettings] = None,
) -> None:

    log_audit(
        action=action_name,
        message=text,
        object_ref=object_ref,
        user_id=user.id if add_user else UserId(""),
        diff_text=diff_text,
    )
    cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

    search.update_index_background(action_name)

    ActivateChangesWriter().add_change(
        action_name,
        text,
        object_ref,
        add_user,
        need_sync,
        need_restart,
        domains,
        sites,
        domain_settings,
    )


class ActivateChangesWriter:
    _enabled = True

    @classmethod
    @contextmanager
    def disable(cls) -> Iterator[None]:
        try:
            cls._enabled = False
            yield
        finally:
            cls._enabled = True

    def add_change(
        self,
        action_name: str,
        text: LogMessage,
        object_ref: Optional[ObjectRef],
        add_user: bool,
        need_sync: Optional[bool],
        need_restart: Optional[bool],
        domains: Optional[List[Type[ABCConfigDomain]]],
        sites: Optional[Iterable[SiteId]],
        domain_settings: Optional[DomainSettings],
    ) -> None:
        if not ActivateChangesWriter._enabled:
            return

        # Default to a core only change
        if domains is None:
            domains = [config_domain_registry["check_mk"]]

        # All replication sites in case no specific site is given
        if sites is None:
            sites = activation_sites().keys()

        change_id = self._new_change_id()

        for site_id in sites:
            self._add_change_to_site(
                site_id,
                change_id,
                action_name,
                text,
                object_ref,
                add_user,
                need_sync,
                need_restart,
                domains,
                domain_settings,
            )

    def _new_change_id(self) -> str:
        return cmk.gui.utils.gen_id()

    def _add_change_to_site(
        self,
        site_id: SiteId,
        change_id: str,
        action_name: str,
        text: LogMessage,
        object_ref: Optional[ObjectRef],
        add_user: bool,
        need_sync: Optional[bool],
        need_restart: Optional[bool],
        domains: List[Type[ABCConfigDomain]],
        domain_settings: Optional[DomainSettings],
    ) -> None:
        # Individual changes may override the domain restart default value
        if need_restart is None:
            need_restart = any(d.needs_activation for d in domains)

        if need_sync is None:
            need_sync = any(d.needs_sync for d in domains)

        # Using attrencode here is against our regular rule to do the escaping
        # at the last possible time: When rendering. But this here is the last
        # place where we can distinguish between HTML() encapsulated (already)
        # escaped / allowed HTML and strings to be escaped.
        text = escaping.escape_text(text)

        # If the local site don't need a restart, there is no reason to add a
        # change for that site. Otherwise the activation page would show a
        # change but the site would not be selected for activation.
        if site_is_local(site_id) and need_restart is False:
            return None

        SiteChanges(SiteChanges.make_path(site_id)).append(
            {
                "id": change_id,
                "action_name": action_name,
                "text": "%s" % text,
                "object": object_ref,
                "user_id": user.id if add_user else None,
                "domains": [d.ident() for d in domains],
                "time": time.time(),
                "need_sync": need_sync,
                "need_restart": need_restart,
                "domain_settings": domain_settings or {},
            }
        )


class SiteChanges(ABCAppendStore[ChangeSpec]):
    """Manage persisted changes of a single site"""

    @staticmethod
    def make_path(*args: str) -> Path:
        return _wato_var_dir() / ("replication_changes_%s.mk" % args[0])

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


def add_service_change(
    host: "CREHost",
    action_name: str,
    text: str,
    diff_text: Optional[str] = None,
    need_sync: bool = False,
) -> None:
    add_change(
        action_name,
        text,
        object_ref=host.object_ref(),
        sites=[host.site_id()],
        diff_text=diff_text,
        need_sync=need_sync,
    )


def make_object_audit_log_url(object_ref: ObjectRef) -> str:
    return makeuri_contextless(
        request,
        [
            ("mode", "auditlog"),
            ("options_object_type", DropdownChoice.option_id(object_ref.object_type)),
            ("options_object_ident", object_ref.ident),
        ],
        filename="wato.py",
    )

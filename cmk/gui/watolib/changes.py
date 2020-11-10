#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Functions for logging changes and keeping the "Activate Changes" state and finally activating changes."""

import ast
import errno
import os
import time
from typing import Dict, Union, TYPE_CHECKING, Optional, Type, List, Iterable, Any
from pathlib import Path

import cmk.utils
import cmk.utils.store as store
from cmk.utils.type_defs import UserId

import cmk.gui.utils
from cmk.gui import config, escaping
from cmk.gui.config import SiteId, SiteConfiguration
from cmk.gui.i18n import _
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKGeneralException

import cmk.gui.watolib.git
import cmk.gui.watolib.sidebar_reload
from cmk.gui.watolib import search

from cmk.gui.plugins.watolib import config_domain_registry, ABCConfigDomain

if TYPE_CHECKING:
    from cmk.gui.watolib.hosts_and_folders import CREFolder, CREHost

LinkInfoObject = Union["CREFolder", "CREHost", str, None]
ChangeSpec = Dict[str, Any]
LogMessage = Union[str, HTML]


def _wato_var_dir() -> Path:
    return Path(cmk.utils.paths.var_dir, "wato")


def audit_log_path() -> Path:
    return _wato_var_dir() / "log" / "audit.log"


def _log_entry(linkinfo: LinkInfoObject,
               action: str,
               message: str,
               user_id: Optional[UserId] = None) -> None:
    if linkinfo and not isinstance(linkinfo, str):
        link = linkinfo.linkinfo()
    else:
        link = linkinfo

    write_tokens = (
        time.strftime("%s"),
        link or "-",
        user_id or config.user.id or "-",
        action,
        message.replace("\n", "\\n"),
    )

    store.makedirs(audit_log_path().parent)
    with audit_log_path().open(mode="a", encoding='utf-8') as f:
        audit_log_path().chmod(0o660)
        f.write(" ".join(write_tokens) + "\n")


def log_audit(linkinfo: LinkInfoObject,
              action: str,
              message: LogMessage,
              user_id: Optional[UserId] = None) -> None:
    if config.wato_use_git:
        if isinstance(message, HTML):
            message = escaping.strip_tags(message.value)
        cmk.gui.watolib.git.add_message(message)
    # Using escape_attribute here is against our regular rule to do the escaping
    # at the last possible time: When rendering. But this here is the last
    # place where we can distinguish between HTML() encapsulated (already)
    # escaped / allowed HTML and strings to be escaped.
    message = escaping.escape_text(message).strip()
    _log_entry(linkinfo, action, message, user_id)


def add_change(action_name: str,
               text: LogMessage,
               obj: LinkInfoObject = None,
               add_user: bool = True,
               need_sync: Optional[bool] = None,
               need_restart: Optional[bool] = None,
               domains: Optional[List[Type[ABCConfigDomain]]] = None,
               sites: Optional[List[SiteId]] = None) -> None:

    log_audit(obj, action_name, text, config.user.id if add_user else UserId(''))
    cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

    search.update_and_store_index_background(action_name)

    # On each change to the Checkmk configuration mark the agents to be rebuild
    # TODO: Really? Why?
    #if has_agent_bakery():
    #    import cmk.gui.cee.agent_bakery as agent_bakery
    #    agent_bakery.mark_need_to_bake_agents()

    ActivateChangesWriter().add_change(action_name, text, obj, add_user, need_sync, need_restart,
                                       domains, sites)


class ActivateChangesWriter:
    def add_change(self, action_name: str, text: LogMessage, obj: LinkInfoObject, add_user: bool,
                   need_sync: Optional[bool], need_restart: Optional[bool],
                   domains: Optional[List[Type[ABCConfigDomain]]],
                   sites: Optional[Iterable[SiteId]]) -> None:
        # Default to a core only change
        if domains is None:
            domains = [config_domain_registry["check_mk"]]

        # All replication sites in case no specific site is given
        if sites is None:
            sites = activation_sites().keys()

        change_id = self._new_change_id()

        for site_id in sites:
            self._add_change_to_site(site_id, change_id, action_name, text, obj, add_user,
                                     need_sync, need_restart, domains)

    def _new_change_id(self) -> str:
        return cmk.gui.utils.gen_id()

    def _add_change_to_site(self, site_id: SiteId, change_id: str, action_name: str,
                            text: LogMessage, obj: LinkInfoObject, add_user: bool,
                            need_sync: Optional[bool], need_restart: Optional[bool],
                            domains: List[Type[ABCConfigDomain]]) -> None:
        # Individual changes may override the domain restart default value
        if need_restart is None:
            need_restart = any([d.needs_activation for d in domains])

        if need_sync is None:
            need_sync = any([d.needs_sync for d in domains])

        def serialize_object(obj):
            if obj is None:
                return None
            return obj.__class__.__name__, obj.ident()

        # Using attrencode here is against our regular rule to do the escaping
        # at the last possible time: When rendering. But this here is the last
        # place where we can distinguish between HTML() encapsulated (already)
        # escaped / allowed HTML and strings to be escaped.
        text = escaping.escape_text(text)

        SiteChanges(site_id).save_change({
            "id": change_id,
            "action_name": action_name,
            "text": "%s" % text,
            "object": serialize_object(obj),
            "user_id": config.user.id if add_user else None,
            "domains": [d.ident for d in domains],
            "time": time.time(),
            "need_sync": need_sync,
            "need_restart": need_restart,
        })


class SiteChanges:
    """Manage persisted changes of a single site"""
    def __init__(self, site_id: SiteId) -> None:
        super(SiteChanges, self).__init__()
        self._site_id = site_id

    def _site_changes_path(self) -> Path:
        return _wato_var_dir() / ("replication_changes_%s.mk" % self._site_id)

    # TODO: Implement this locking as context manager
    def load(self, lock: bool = False) -> List[ChangeSpec]:
        """Parse the site specific changes file

        The file format has been choosen to be able to append changes without
        much cost. This is just a intermmediate format for 1.4.x. In 1.5 we will
        reimplement WATO changes and this very specific file format will vanish."""
        path = self._site_changes_path()

        if lock:
            store.aquire_lock(path)

        changes = []
        try:
            with path.open("rb") as f:
                for entry in f.read().split(b"\0"):
                    if entry:
                        changes.append(ast.literal_eval(entry.decode("utf-8")))
        except IOError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise
        except Exception:
            if lock:
                store.release_lock(path)
            raise

        return changes

    def save(self, changes: List[ChangeSpec]) -> None:
        # First truncate the file
        with self._site_changes_path().open("wb"):
            pass

        for change_spec in changes:
            self.save_change(change_spec)

    def save_change(self, change_spec: ChangeSpec) -> None:
        path = self._site_changes_path()
        try:
            store.aquire_lock(path)

            with path.open("ab+") as f:
                f.write(repr(change_spec).encode("utf-8") + b"\0")
                f.flush()
                os.fsync(f.fileno())

            path.chmod(0o660)

        except Exception as e:
            raise MKGeneralException(_("Cannot write file \"%s\": %s") % (path, e))

        finally:
            store.release_lock(path)

    def clear(self) -> None:
        try:
            self._site_changes_path().unlink()
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass  # Not existant -> OK
            else:
                raise


def add_service_change(host: "CREHost",
                       action_name: str,
                       text: str,
                       need_sync: bool = False) -> None:
    add_change(action_name, text, obj=host, sites=[host.site_id()], need_sync=need_sync)


def activation_sites() -> Dict[SiteId, SiteConfiguration]:
    """Returns the list of sites that are affected by WATO changes
    These sites are shown on activation page and get change entries
    added during WATO changes."""
    return {
        site_id: site
        for site_id, site in config.user.authorized_sites(
            unfiltered_sites=config.configured_sites()).items()
        if config.site_is_local(site_id) or site.get("replication")
    }

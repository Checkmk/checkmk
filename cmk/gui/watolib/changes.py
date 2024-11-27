#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Functions for logging changes and keeping the "Activate Changes" state and finally activating changes."""

import time
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager

from livestatus import SiteId

import cmk.utils
from cmk.utils.setup_search_index import request_index_update
from cmk.utils.user import UserId

import cmk.gui.utils
import cmk.gui.watolib.git
import cmk.gui.watolib.sidebar_reload
from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.site_config import site_is_local
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils import escaping
from cmk.gui.watolib.audit_log import log_audit, LogMessage
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_domain_registry,
    DomainSettings,
)
from cmk.gui.watolib.objref import ObjectRef
from cmk.gui.watolib.site_changes import SiteChanges


def add_change(
    action_name: str,
    text: LogMessage,
    object_ref: ObjectRef | None = None,
    diff_text: str | None = None,
    add_user: bool = True,
    need_sync: bool | None = None,
    need_restart: bool | None = None,
    need_apache_reload: bool | None = None,
    domains: Sequence[ABCConfigDomain] | None = None,
    sites: Sequence[SiteId] | None = None,
    domain_settings: DomainSettings | None = None,
    prevent_discard_changes: bool = False,
) -> None:
    """
    config_domains:
        list of config domains that are affected by this change
    """
    log_audit(
        action=action_name,
        message=text,
        object_ref=object_ref,
        user_id=user.id if add_user else UserId(""),
        diff_text=diff_text,
    )
    cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

    request_index_update(action_name)

    ActivateChangesWriter().add_change(
        action_name,
        text,
        object_ref,
        add_user,
        need_sync,
        need_restart,
        need_apache_reload,
        domains,
        sites,
        domain_settings,
        prevent_discard_changes,
        diff_text=diff_text,
    )


class ActivateChangesWriter:
    _enabled = True

    @classmethod
    @contextmanager
    def disable(cls) -> Iterator[None]:
        cls._enabled = False
        try:
            yield
        finally:
            cls._enabled = True

    def add_change(
        self,
        action_name: str,
        text: LogMessage,
        object_ref: ObjectRef | None,
        add_user: bool,
        need_sync: bool | None,
        need_restart: bool | None,
        need_apache_reload: bool | None,
        domains: Sequence[ABCConfigDomain] | None,
        sites: Iterable[SiteId] | None,
        domain_settings: DomainSettings | None,
        prevent_discard_changes: bool = False,
        diff_text: str | None = None,
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
                need_apache_reload,
                domains,
                domain_settings,
                prevent_discard_changes,
                diff_text,
            )

    def _new_change_id(self) -> str:
        return cmk.gui.utils.gen_id()

    def _add_change_to_site(
        self,
        site_id: SiteId,
        change_id: str,
        action_name: str,
        text: LogMessage,
        object_ref: ObjectRef | None,
        add_user: bool,
        need_sync: bool | None,
        need_restart: bool | None,
        need_apache_reload: bool | None,
        domains: Sequence[ABCConfigDomain],
        domain_settings: DomainSettings | None,
        prevent_discard_changes: bool,
        diff_text: str | None = None,
    ) -> None:
        # Individual changes may override the domain restart default value
        if need_restart is None:
            need_restart = any(d.needs_activation for d in domains)

        if need_sync is None:
            need_sync = any(d.needs_sync for d in domains)

        # Only changes are currently capable of requesting an apache reload not the entire domain
        if need_apache_reload is None:
            need_apache_reload = False

        # Using attrencode here is against our regular rule to do the escaping
        # at the last possible time: When rendering. But this here is the last
        # place where we can distinguish between HTML() encapsulated (already)
        # escaped / allowed HTML and strings to be escaped.
        text = escaping.escape_text(text)

        SiteChanges(site_id).append(
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
                "prevent_discard_changes": prevent_discard_changes,
                "diff_text": diff_text,
                "has_been_activated": site_is_local(active_config, site_id)
                and need_restart is False
                and need_apache_reload is False,
            }
        )


def add_service_change(
    action_name: str,
    text: str,
    object_ref: ObjectRef,
    site_id: SiteId,
    diff_text: str | None = None,
    need_sync: bool = False,
) -> None:
    add_change(
        action_name,
        text,
        object_ref=object_ref,
        sites=[site_id],
        diff_text=diff_text,
        need_sync=need_sync,
    )

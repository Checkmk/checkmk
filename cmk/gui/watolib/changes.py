#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Functions for logging changes and keeping the "Activate Changes" state and finally activating changes."""

import time
from contextlib import contextmanager
from typing import Iterable, Iterator, List, Optional, Type

from livestatus import SiteId

import cmk.utils
from cmk.utils.type_defs import UserId

import cmk.gui.utils
import cmk.gui.watolib.git
import cmk.gui.watolib.sidebar_reload
from cmk.gui.logged_in import user
from cmk.gui.plugins.watolib.utils import ABCConfigDomain, config_domain_registry, DomainSettings
from cmk.gui.site_config import site_is_local
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils import escaping
from cmk.gui.watolib import search
from cmk.gui.watolib.audit_log import log_audit, LogMessage
from cmk.gui.watolib.objref import ObjectRef
from cmk.gui.watolib.site_changes import SiteChanges


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


def add_service_change(
    action_name: str,
    text: str,
    object_ref: ObjectRef,
    site_id: SiteId,
    diff_text: Optional[str] = None,
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

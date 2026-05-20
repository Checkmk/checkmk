#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Free functions for recording pending configuration changes.

``add_change`` and ``add_service_change`` build a request-scoped
:class:`PendingChanges` on every call and delegate to it. New code should
construct a :class:`PendingChanges` once at the request boundary and pass it
down explicitly.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.user_sites import activation_sites

from .audit_log import LogMessage, make_audit_log_change_hook
from .config_domain_name import ABCConfigDomain, DomainSettings
from .objref import ObjectRef
from .pending_changes import (
    Change,
    ChangeHook,
    ChangeScope,
    index_update_change_hook,
    NoopPendingChangesStore,
    PendingChanges,
    PendingChangesStore,
)
from .sidebar_reload import sidebar_reload_change_hook

_RECORDING_ENABLED = True


def _default_hooks(*, use_git: bool) -> tuple[ChangeHook, ...]:
    return (
        make_audit_log_change_hook(use_git=use_git),
        sidebar_reload_change_hook,
        index_update_change_hook,
    )


def _scope_from_sites(sites: Sequence[SiteId] | None) -> ChangeScope:
    if sites is None:
        return ChangeScope.all_activation_sites()
    return ChangeScope.sites(sites)


def add_change(
    *,
    action_name: str,
    text: LogMessage,
    user_id: UserId | None,
    use_git: bool,
    domains: Sequence[ABCConfigDomain],
    object_ref: ObjectRef | None = None,
    diff_text: str | None = None,
    need_sync: bool | None = None,
    need_restart: bool | None = None,
    need_apache_reload: bool | None = None,
    sites: Sequence[SiteId] | None = None,
    domain_settings: DomainSettings | None = None,
    prevent_discard_changes: bool = False,
) -> None:
    """Record a pending configuration change.

    Builds a :class:`PendingChanges` from the current ``active_config``,
    ``omd_site()``, and ``use_git`` flag, then delegates.
    """
    store: PendingChangesStore = (
        PendingChangesStore() if _RECORDING_ENABLED else NoopPendingChangesStore()
    )
    pending_changes = PendingChanges(
        activation_sites=activation_sites(active_config.sites),
        local_site=omd_site(),
        acting_user=user_id,
        store=store,
        hooks=_default_hooks(use_git=use_git),
    )
    pending_changes.add(
        Change(
            action_name=action_name,
            text=text,
            domains=[d.ident() for d in domains],
            domain_settings=domain_settings or {},
            object_ref=object_ref,
            diff_text=diff_text,
            force_sync=need_sync,
            force_restart=need_restart,
            force_apache_reload=bool(need_apache_reload),
            prevent_discard_changes=prevent_discard_changes,
        ),
        _scope_from_sites(sites),
    )


def add_service_change(
    *,
    action_name: str,
    text: str,
    user_id: UserId | None,
    object_ref: ObjectRef,
    domains: Sequence[ABCConfigDomain],
    domain_settings: DomainSettings,
    site_id: SiteId,
    use_git: bool,
    diff_text: str | None = None,
    need_sync: bool = False,
) -> None:
    add_change(
        action_name=action_name,
        text=text,
        user_id=user_id,
        object_ref=object_ref,
        sites=[site_id],
        diff_text=diff_text,
        need_sync=need_sync,
        domains=domains,
        domain_settings=domain_settings,
        use_git=use_git,
    )


class ActivateChangesWriter:
    """Provides a ``disable()`` context manager that suppresses :func:`add_change` writes."""

    @classmethod
    @contextmanager
    def disable(cls) -> Iterator[None]:
        global _RECORDING_ENABLED
        _RECORDING_ENABLED = False
        try:
            yield
        finally:
            _RECORDING_ENABLED = True

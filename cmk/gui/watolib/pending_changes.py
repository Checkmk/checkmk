#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Abstractions for recording pending configuration changes."""

import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.misc import gen_id
from cmk.gui.utils.speaklater import LazyString
from cmk.utils.setup_search_index import request_index_update

from .config_domain_name import ConfigDomainName, SerializedSettings
from .objref import ObjectRef
from .site_changes import ChangeSpec, SiteChanges


@dataclass(frozen=True, kw_only=True, slots=True)
class Change:
    """Describes a configuration change a caller wants to record.

    ``force_restart`` and ``force_sync`` override the default activation
    behavior derived from the change's domains:

    * ``None`` (default) - defer to the domain defaults at read time.
    * ``True`` - force the flag on, even if the domains would not require it.
    * ``False`` - suppress the flag, even if the domains would require it.
    """

    action_name: str
    text: str | HTML | LazyString
    domains: Iterable[ConfigDomainName]
    domain_settings: Mapping[ConfigDomainName, SerializedSettings] = field(default_factory=dict)
    object_ref: ObjectRef | None = None
    diff_text: str | None = None
    force_restart: bool | None = None
    force_sync: bool | None = None
    force_apache_reload: bool = False
    prevent_discard_changes: bool = False


class _ScopeKind(Enum):
    ALL_ACTIVATION_SITES = "all_activation_sites"
    EXPLICIT_SITES = "explicit_sites"
    LOCAL_SITE = "local_site"


@dataclass(frozen=True, slots=True)
class ChangeScope:
    """The set of sites a change applies to.

    Construct via the classmethods rather than the dataclass fields:

    * :meth:`all_activation_sites` - every site participating in activation.
    * :meth:`sites` - a caller-specified set, intersected with the
      activation sites at record time. If the intersection drops sites, the
      local site is added so the change is still logged somewhere.
    * :meth:`local_site` - only the local site.
    """

    kind: _ScopeKind
    explicit_sites: frozenset[SiteId] = frozenset()

    @classmethod
    def all_activation_sites(cls) -> "ChangeScope":
        return cls(kind=_ScopeKind.ALL_ACTIVATION_SITES)

    @classmethod
    def sites(cls, site_ids: Iterable[SiteId]) -> "ChangeScope":
        return cls(kind=_ScopeKind.EXPLICIT_SITES, explicit_sites=frozenset(site_ids))

    @classmethod
    def local_site(cls) -> "ChangeScope":
        return cls(kind=_ScopeKind.LOCAL_SITE)


@dataclass(frozen=True, slots=True)
class ChangeEvent:
    """Payload passed to every :data:`ChangeHook` after a change is recorded."""

    request: Change
    user_id: UserId | None
    affected_sites: frozenset[SiteId]


ChangeHook = Callable[[ChangeEvent], None]


class PendingChangesStore:
    """Persists per-site change entries to disk."""

    def append(self, site_id: SiteId, entry: ChangeSpec) -> None:
        SiteChanges(site_id).append(entry)


class NoopPendingChangesStore(PendingChangesStore):
    """A :class:`PendingChangesStore` that discards everything."""

    def append(self, site_id: SiteId, entry: ChangeSpec) -> None:
        return None


class PendingChanges:
    """Records pending configuration changes."""

    def __init__(
        self,
        *,
        activation_sites: SiteConfigurations,
        local_site: SiteId,
        acting_user: UserId | None,
        store: PendingChangesStore,
        hooks: Sequence[ChangeHook],
    ) -> None:
        self._activation_sites = activation_sites
        self._local_site = local_site
        self._acting_user = acting_user
        self._store = store
        self._hooks = tuple(hooks)

    def add(self, request: Change, scope: ChangeScope) -> None:
        affected = self._resolve_scope(scope)
        change_id = gen_id()
        now = time.time()
        # Escaping the text here is the last point at which we can
        # distinguish HTML-marked-as-safe from plain text needing escaping.
        text = str(escaping.escape_text(request.text))
        domains = list(request.domains)
        entry = ChangeSpec(
            {
                "id": change_id,
                "action_name": request.action_name,
                "text": text,
                "object": request.object_ref,
                "user_id": self._acting_user,
                "domains": domains,
                "time": now,
                "force_sync": request.force_sync,
                "force_restart": request.force_restart,
                "force_apache_reload": request.force_apache_reload,
                "domain_settings": dict(request.domain_settings),
                "prevent_discard_changes": request.prevent_discard_changes,
                "diff_text": request.diff_text,
            }
        )
        for site_id in affected:
            self._store.append(site_id, entry)
        event = ChangeEvent(
            request=request,
            user_id=self._acting_user,
            affected_sites=affected,
        )
        for hook in self._hooks:
            hook(event)

    def _resolve_scope(self, scope: ChangeScope) -> frozenset[SiteId]:
        valid = frozenset(self._activation_sites)
        if scope.kind is _ScopeKind.ALL_ACTIVATION_SITES:
            return valid
        if scope.kind is _ScopeKind.LOCAL_SITE:
            return frozenset({self._local_site})
        intersected = scope.explicit_sites & valid
        if len(intersected) != len(scope.explicit_sites):
            # A caller-supplied site was filtered out (e.g. a remote site
            # name that the local instance does not know). Make sure the
            # change is still logged locally so it is visible.
            return intersected | {self._local_site}
        return intersected


def index_update_change_hook(event: ChangeEvent) -> None:
    request_index_update(event.request.action_name)

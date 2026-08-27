#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Scope-derived narrowing of what an authenticated request may do."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar, Final

import flask

from cmk.gui.scopes import normalize_scopes, ScopeId

# Allow-list of the permissions "compatible with" a read scope.
# PRELIMINARY LIST, extend as we go.
READ_PERMISSIONS: Final[frozenset[str]] = frozenset(
    {
        # Not a read capability but the prerequisite for any request at all.
        "general.use",
        # hosts/services/comments/downtimes/EC/folders
        "bi.see_all",
        "general.see_all",
        "mkeventd.seeall",
        "wato.see_all_folders",
        # get_config_changes
        "wato.auditlog",
        # get_availability
        "general.see_availability",
    }
)

# ScopeId.WRITE has no entry here, as there is no allow-list for write: the global read-write scope
# means "unrestricted". But any more fine-grained scope would be added here.
_PERMISSIONS_BY_SCOPE: Final[dict[ScopeId, frozenset[str]]] = {
    ScopeId.READ: READ_PERMISSIONS,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class Authorization:
    """What the credential presented with this request permits, before roles.

    Intersected with the user's role permissions in LoggedInUser.may(), so it can only take
    permissions away.

    The only kind of credential that restricts authorization beyond role permissions today are
    scoped OAuth tokens.
    """

    unrestricted: bool = False
    allowed_permissions: frozenset[str] = frozenset()

    UNRESTRICTED: ClassVar[Authorization]  # i.e. the global read-write scope

    def __post_init__(self) -> None:
        if self.unrestricted and self.allowed_permissions:
            raise RuntimeError("If unrestricted do not set permissions")

    def permits(self, permission_name: str) -> bool:
        return self.unrestricted or permission_name in self.allowed_permissions

    @classmethod
    def from_scopes(cls, scopes: Iterable[ScopeId]) -> Authorization:
        """Resolve scopes to permissions."""
        granted = normalize_scopes(scopes)
        if ScopeId.WRITE in granted:
            return cls.UNRESTRICTED
        permissions: set[str] = set()
        for scope in granted:
            permissions |= _PERMISSIONS_BY_SCOPE.get(scope, frozenset())
        return cls(allowed_permissions=frozenset(permissions))


Authorization.UNRESTRICTED = Authorization(unrestricted=True)


def request_authorization() -> Authorization:
    """The current request's Authorization, UNRESTRICTED outside a request context."""
    # Not using our ctx_stack wrapper (aka "Working outside of request context.") but flask.session
    # directly: The wrapper's whole point is that error message, but we'd only catch and drop it in
    # the fallback case below.
    try:
        # flask types this as its own session class; `authorization` is on ours.
        authorization = flask.session.authorization  # type: ignore[attr-defined]
    except (RuntimeError, AttributeError):
        # Expected for background jobs, cron, CLI, ...
        return Authorization.UNRESTRICTED
    assert isinstance(authorization, Authorization)
    return authorization

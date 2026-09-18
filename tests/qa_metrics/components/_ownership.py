#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Resolve repository paths to the components that own them.

Ownership is declared by the repository's ``OWNERS`` files and served by Gerrit's
code-owners API, read through ``cwz``'s ``CodeOwnersClient``. This module wraps
that client so callers get a plain immutable mapping and deal with no async,
credentials or ``", "``-joined component strings.

Ownership comes from ``branch`` on the Gerrit server, not from the local
checkout: a source file added on a feature branch is unowned until it is merged.
Data that loaded but attributes nothing is refused rather than returned, so no
caller has to tell a failed fetch from an empty repository.

It is the only place touching ``cwz``'s library API, which is not stable across
releases -- 0.3.8 renamed both the credential helper and the data-loading method
-- so a version bump is one edit here.
"""

import asyncio
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

from cwz.credentials import resolve_credentials
from cwz.gerrit_utils.client import (
    CodeOwnersClient,
    DEFAULT_BRANCH,
    DEFAULT_GERRIT_URL,
    DEFAULT_PROJECT_NAME,
    GerritClient,
)


class OwnershipUnavailableError(RuntimeError):
    """Ownership data that loaded but cannot attribute a single path."""


class UnknownComponentError(LookupError):
    """A component id that the repository's ``OWNERS`` files do not define."""

    def __init__(self, component_id: str, known: Collection[str]) -> None:
        suggestions = get_close_matches(component_id, sorted(known), n=5)
        hint = f" Did you mean {', '.join(suggestions)}?" if suggestions else ""
        super().__init__(
            f"Unknown component {component_id!r} ({len(known)} components defined).{hint}"
        )


@dataclass(frozen=True)
class ComponentOwnership:
    """Ownership of a fixed set of repository paths.

    ``owners_by_path`` holds one entry per path handed to :func:`load_ownership`,
    empty when no ``OWNERS`` rule applies. A path may have several owners, so
    per-component file sets overlap and do not add up to the whole.
    """

    owners_by_path: Mapping[Path, Sequence[str]]
    component_ids: frozenset[str]

    def owners_of(self, path: Path) -> Sequence[str]:
        """Ids of the components owning ``path``; empty if unowned or unresolved."""
        return self.owners_by_path.get(path, [])

    def paths_owned_by(self, component_id: str) -> list[Path]:
        """The resolved paths ``component_id`` owns, sorted.

        Raises :class:`UnknownComponentError` rather than returning an empty
        list, which could not be told from a component owning none of these paths.
        """
        if component_id not in self.component_ids:
            raise UnknownComponentError(component_id, self.component_ids)
        return sorted(
            path for path, owners in self.owners_by_path.items() if component_id in owners
        )


def load_ownership(
    paths: Sequence[Path],
    *,
    gerrit_url: str = DEFAULT_GERRIT_URL,
    project: str = DEFAULT_PROJECT_NAME,
    branch: str = DEFAULT_BRANCH,
    credentials: tuple[str, str] | None = None,
) -> ComponentOwnership:
    """Resolve ``paths`` (repository-relative) to their owning components.

    Raises :exc:`OwnershipUnavailableError` when the fetched data attributes
    nothing, which would otherwise read as a repository owned by no one.

    ``credentials`` is a ``(username, api_token)`` pair. Passing it explicitly
    keeps a headless caller's environment variable names out of this module;
    without it ``cwz`` resolves them from ``~/.netrc`` or the keyring -- and
    failing that prompts, or exits the process outright when stdout is not a
    tty. A headless caller therefore passes them.
    """
    return asyncio.run(
        _resolve(
            paths,
            gerrit_url=gerrit_url,
            project=project,
            branch=branch,
            credentials=credentials,
        )
    )


async def _resolve(
    paths: Sequence[Path],
    *,
    gerrit_url: str,
    project: str,
    branch: str,
    credentials: tuple[str, str] | None,
) -> ComponentOwnership:
    username, password = credentials or resolve_credentials(
        service="Gerrit",
        url=gerrit_url,
        token_hint=f"{gerrit_url}/settings/#HTTPCredentials",
    )
    async with (
        GerritClient(gerrit_url, username, password) as gerrit_client,
        # The CodeOwnersClient context is what persists the on-disk cache, on
        # exit -- without it every run would refetch all ownership data.
        CodeOwnersClient(gerrit_client, project, branch) as owners_client,
    ):
        await owners_client.initialize_data(cache_mode="auto")
        components = await owners_client.all_components_info(with_code_locations=True)
        _assert_usable(
            component_count=len(components),
            rule_count=sum(len(component.code_location or ()) for component in components.values()),
        )
        # with_code_locations loaded the OWNERS entries, so component_for_path, which
        # would otherwise fetch every OWNERS file on its first call, costs no request.
        return ComponentOwnership(
            owners_by_path={
                path: _owner_ids(await owners_client.component_for_path(str(path)))
                for path in paths
            },
            component_ids=frozenset(components),
        )


def _assert_usable(*, component_count: int, rule_count: int) -> None:
    """Refuse ownership data that would answer "unowned" for every path."""
    if not component_count:
        raise OwnershipUnavailableError(
            "The ownership data defines no component at all, so every path would resolve to "
            "unowned."
        )
    if not rule_count:
        raise OwnershipUnavailableError(
            f"The ownership data defines {component_count} component(s) but not one OWNERS rule, "
            "so every path would resolve to unowned."
        )


def _owner_ids(joined: str | None) -> list[str]:
    """Split ``component_for_path``'s ``", "``-joined ids (``None`` when unowned).

    Component ids hold only ``[a-z0-9_]``, so the join is reversible.
    """
    return joined.split(", ") if joined else []

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Resolve repository paths to the components that own them.

Ownership is declared by the repository's ``OWNERS`` files, read from a local
checkout through ``cwz``'s ``LocalRepo`` and ``CodeOwnership``. This module wraps
them so callers get a plain immutable mapping and deal with no async or
``", "``-joined component strings.

Ownership is that of the checkout as it is on disk, untracked files included, so
it matches whatever else a caller reads from the same tree. Data that loaded but
attributes nothing is refused rather than returned, so no caller has to tell a
broken checkout from a repository owned by no one.

It is the only place touching ``cwz``'s library API, which is not stable across
releases -- 0.4.8 moved ownership out of ``CodeOwnersClient`` -- so a version bump
is one edit here.
"""

import asyncio
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path, PurePosixPath

from cwz.code_ownership import CodeOwnership, LocalRepo


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


def load_ownership(repo_root: Path, paths: Sequence[Path]) -> ComponentOwnership:
    """Resolve ``paths`` (relative to ``repo_root``) to their owning components.

    ``repo_root`` must be the toplevel of a git checkout. Raises
    :exc:`OwnershipUnavailableError` when the checkout's data attributes nothing,
    which would otherwise read as a repository owned by no one.
    """
    return asyncio.run(_resolve(CodeOwnership(LocalRepo(repo_root)), paths))


async def _resolve(ownership: CodeOwnership, paths: Sequence[Path]) -> ComponentOwnership:
    components = await ownership.all_components_info(with_code_locations=True)
    _assert_usable(
        component_count=len(components),
        rule_count=sum(len(component.code_location or ()) for component in components.values()),
    )
    return ComponentOwnership(
        owners_by_path={
            path: _owner_ids(await ownership.component_for_path(PurePosixPath(path)))
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

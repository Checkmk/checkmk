#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

from cmk.schema_manager.errors import InvalidRevisionChainError


class Revision[ContextT](ABC):
    """A single schema change.

    Subclass it once per revision and set `id` as a class attribute.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Identifies this revision; unique within its chain."""

    @abstractmethod
    def upgrade(self, context: ContextT) -> None:
        """Apply this revision's schema change to `context`.

        Runs inside the backend's transaction and must not end it.
        """


@dataclass(frozen=True)
class RevisionChain[ContextT]:
    """A non-empty, ordered sequence of revisions with unique ids.

    Append-only once shipped: a database records only the id of its last
    applied revision.
    """

    revisions: tuple[Revision[ContextT], ...]

    def __post_init__(self) -> None:
        if not self.revisions:
            raise InvalidRevisionChainError("RevisionChain must not be empty")
        seen: set[str] = set()
        duplicates: set[str] = set()
        for revision in self.revisions:
            if revision.id in seen:
                duplicates.add(revision.id)
            seen.add(revision.id)
        if duplicates:
            raise InvalidRevisionChainError(
                f"RevisionChain has duplicate revision ids: {sorted(duplicates)}"
            )

    def __iter__(self) -> Iterator[Revision[ContextT]]:
        return iter(self.revisions)

    def __len__(self) -> int:
        return len(self.revisions)

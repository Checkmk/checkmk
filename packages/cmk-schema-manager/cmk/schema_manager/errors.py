#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Sequence


class SchemaManagerError(Exception):
    """Base class of every error the schema manager raises on its own."""


class InvalidRevisionChainError(SchemaManagerError, ValueError):
    """A `RevisionChain` was constructed from invalid revisions."""


class SchemaVersionAheadError(SchemaManagerError):
    """Raised when the database is at a revision the chain does not contain."""

    def __init__(self, revision_id: str) -> None:
        super().__init__(
            f"The database is at revision {revision_id!r}, "
            "which the current revision chain does not contain"
        )
        self.revision_id = revision_id


class ForeignKeyViolationError(SchemaManagerError):
    """A revision added rows that violate a foreign key."""

    def __init__(self, revision_id: str, violations: Sequence[tuple[str, str]]) -> None:
        super().__init__(
            f"Revision {revision_id!r} added rows that violate foreign keys "
            f"(table, parent table): {list(violations)}"
        )
        self.revision_id = revision_id
        self.violations = violations


class BackendUnavailableError(SchemaManagerError):
    """A backend's connection could not be opened or used."""

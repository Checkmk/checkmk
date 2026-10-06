#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The interface the schema-migration mechanism goes through; each database kind implements it fully."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from logging import Logger

from cmk.schema_manager.revision import RevisionChain


class Backend[ContextT](ABC):
    """Stateless: the database is passed by name on every call."""

    @abstractmethod
    def connect(self, name: str, *, create: bool = False) -> AbstractContextManager[ContextT]:
        """Open a connection/session to the database named `name`.

        A missing database is an error unless `create` is set.
        """

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Whether the database named `name` exists, without creating it."""

    @abstractmethod
    def apply_pending(
        self, context: ContextT, chain: RevisionChain[ContextT], logger: Logger
    ) -> None:
        """Apply every revision of `chain` not yet applied to `context`."""

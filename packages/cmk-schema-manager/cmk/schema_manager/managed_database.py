#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# A type parameter's bound cannot refer to another one, so any backend is Backend[Any].
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Literal

from cmk.schema_manager.backend.base import Backend
from cmk.schema_manager.revision import RevisionChain

OmdLifecycleEvent = Literal["create", "update"]


@dataclass(frozen=True)
class ManagedDatabase[ContextT, BackendT: Backend[Any] = Backend[ContextT]]:
    """A component's database: what backs it, its revisions, and when omd manages it."""

    name: str
    backend: BackendT
    chain: RevisionChain[ContextT]
    omd_lifecycle: Sequence[OmdLifecycleEvent]

    def connect(self, *, create: bool = False) -> AbstractContextManager[ContextT]:
        return self.backend.connect(self.name, create=create)

    def exists(self) -> bool:
        """Without creating it."""
        return self.backend.exists(self.name)

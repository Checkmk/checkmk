#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test support for adopters of `cmk.schema_manager`."""

from __future__ import annotations

from collections.abc import Callable
from typing import override

from cmk.schema_manager.revision import Revision


class FakeRevision[ContextT](Revision[ContextT]):
    def __init__(self, id_: str, upgrade: Callable[[ContextT], None] = lambda _: None) -> None:
        self._id = id_
        self._upgrade = upgrade

    @property
    @override
    def id(self) -> str:
        return self._id

    @override
    def upgrade(self, context: ContextT) -> None:
        self._upgrade(context)

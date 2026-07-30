#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What the monitor domain needs from a legacy view command.

Described here as protocols so the legacy command registry can be injected into this
domain without it knowing about the monitor world, and without this module importing it.
The members are read-only properties on purpose: that keeps them covariant, so a class
holding plain attributes satisfies these without any adapter on the legacy side.
"""

from collections.abc import Callable, Iterable, Sequence
from typing import Protocol

from cmk.gui.utils.speaklater import LazyString


class LegacyPermission(Protocol):
    @property
    def name(self) -> str: ...


class LegacyCommand(Protocol):
    @property
    def ident(self) -> str: ...
    @property
    def title(self) -> LazyString: ...
    @property
    def icon_name(self) -> str: ...
    @property
    def tables(self) -> Sequence[str]: ...
    @property
    def permission(self) -> LegacyPermission: ...
    @property
    def is_shortcut(self) -> bool: ...
    @property
    def is_suggested(self) -> bool: ...
    @property
    def enabled(self) -> Callable[[], bool]: ...


class LegacyCommandSource(Protocol):
    def values(self) -> Iterable[LegacyCommand]: ...

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What this domain needs from the legacy view's host menus.

The "Host" and "Services" dropdowns of the legacy "Services of host" view are not a fixed
list: they are derived from every visual sharing a host context, so they also carry the
HW/SW inventory views a host happens to have data for and whatever views a user defined
themselves. Deriving them is legacy work, and this domain wants the result without knowing
how it is produced.

Described here as protocols so the legacy side can be injected without this module
importing it, and without it knowing about the monitor world. The members are read-only
properties on purpose: that keeps them covariant, so a class holding plain attributes
satisfies these without any adapter on the legacy side.
"""

from collections.abc import Sequence
from typing import Protocol

from cmk.gui.type_defs import DynamicIcon, StaticIcon


class LegacyHostMenuEntry(Protocol):
    @property
    def ident(self) -> str | None: ...
    @property
    def title(self) -> str: ...
    @property
    def icon(self) -> StaticIcon | DynamicIcon: ...
    @property
    def url(self) -> str: ...
    @property
    def is_show_more(self) -> bool: ...


class LegacyHostMenuTopic(Protocol):
    @property
    def title(self) -> str: ...
    @property
    def entries(self) -> Sequence[LegacyHostMenuEntry]: ...


class LegacyHostMenu(Protocol):
    @property
    def ident(self) -> str: ...
    @property
    def title(self) -> str: ...
    @property
    def topics(self) -> Sequence[LegacyHostMenuTopic]: ...


class LegacyHostMenuSource(Protocol):
    def host_menus(self, *, hostname: str, site_id: str) -> Sequence[LegacyHostMenu]: ...

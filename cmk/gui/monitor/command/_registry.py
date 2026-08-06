#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The commands the monitoring pages may offer on a host or service.

The monitor domain owns this registry so the monitoring pages describe their
actions without reaching into the legacy view layer. Whoever implements a
command registers it here; the view command layer seeds every one of its
commands automatically, so the monitoring pages see them without importing it.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, override

from cmk.ccc.plugin_registry import Registry
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.utils.speaklater import LazyString

MonitorObjectType = Literal["host", "service"]


@dataclass(frozen=True, kw_only=True)
class MonitorCommand:
    ident: str
    title: LazyString
    icon: str
    object_types: frozenset[MonitorObjectType]
    permission_name: str
    is_prominent: bool
    is_enabled: Callable[[], bool]

    def applies_to(self, object_type: MonitorObjectType) -> bool:
        return object_type in self.object_types

    def is_permitted_for(self, user: LoggedInUser) -> bool:
        return self.is_enabled() and user.may(self.permission_name)


class MonitorCommandRegistry(Registry[MonitorCommand]):
    @override
    def plugin_name(self, instance: MonitorCommand) -> str:
        return instance.ident


monitor_command_registry = MonitorCommandRegistry()

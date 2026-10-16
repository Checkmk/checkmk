#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The configuration of notifications and alert handling"""

import dataclasses
from collections.abc import Sequence
from typing import Literal

from cmk.events.notify_types import (
    EventRule,
    NotificationParameterSpecs,
    NotificationPluginNameStr,
    NotifyPluginParamsDict,
)


@dataclasses.dataclass(frozen=True, kw_only=True)
class AlertHandlingConfigFields:
    alert_handler_event_types: Sequence[Literal["statechange", "checkresult"]] = dataclasses.field(
        default_factory=lambda: ["statechange"]
    )
    alert_logging: int = 20
    alert_handler_timeout: int = 60
    alert_handler_rules: Sequence[EventRule] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True, kw_only=True)
class NotifyConfigFields:
    notification_logging: int = 15
    notification_backlog: int = 10
    enable_rulebased_notifications: bool = True
    notification_fallback_email: str = ""
    notification_fallback_format: tuple[NotificationPluginNameStr, NotifyPluginParamsDict] = (
        "asciimail",
        {},
    )
    notification_rules: Sequence[EventRule] = dataclasses.field(default_factory=list)
    notification_parameter: NotificationParameterSpecs = dataclasses.field(default_factory=dict)
    notification_bulk_interval: int = 10
    notification_plugin_timeout: int = 60
    notification_spooling: bool | Literal["local", "remote", "both", "off"] | None = None
    notification_spool_to: object = None

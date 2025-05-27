#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass, field
from typing import Literal

from cmk.gui.quick_setup.v0_unstable.widgets import Widget


@dataclass(frozen=True, kw_only=True)
class ConditionalNotificationStageWidget(Widget):
    """The conditional notification event stage widgets are a really specific solution to a really
    specific use case for the notification quick setup. Hence, we opted for a really specific
    solution which exactly covers the three use cases we have in the notification quick setup.
    A more generic approach has been rejected, but may be considered in the future."""

    items: list[Widget] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ConditionalNotificationServiceEventStageWidget(ConditionalNotificationStageWidget):
    widget_type: str = field(
        default="conditional_notification_service_event_stage_widget", init=False
    )


@dataclass(frozen=True, kw_only=True)
class ConditionalNotificationECAlertStageWidget(ConditionalNotificationStageWidget):
    widget_type: str = field(default="conditional_notification_ec_alert_stage_widget", init=False)


@dataclass(frozen=True, kw_only=True)
class ConditionalNotificationDialogWidget(ConditionalNotificationStageWidget):
    widget_type: str = field(default="conditional_notification_dialog_widget", init=False)
    target: Literal["svc_filter", "recipient"]

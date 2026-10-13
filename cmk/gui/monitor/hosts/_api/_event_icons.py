#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Self

from cmk.gui.i18n import _
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.shared_typing.icon import IconNames

from .._models import Event


@api_model
class EventIcon:
    """The icon of a monitoring log entry, resolved the way the legacy ``log_icon`` painter does."""

    icon_name: str = api_field(
        description="Icon to render for this event", example=IconNames.alert_crit.value
    )
    title: str = api_field(description="Tooltip shown for the event icon", example="Service alert")

    @classmethod
    def from_event(cls, event: Event) -> Self | None:
        """Build the icon of an event, `None` for an event the legacy view renders without one."""
        if event.type == "SERVICE ALERT":
            icon = {
                0: IconNames.alert_ok,
                1: IconNames.alert_warn,
                2: IconNames.alert_crit,
                3: IconNames.alert_unknown,
            }.get(event.state)
            return None if icon is None else cls(icon_name=icon.value, title=_("Service alert"))

        if event.type == "HOST ALERT":
            icon = {
                0: IconNames.alert_up,
                1: IconNames.alert_down,
                2: IconNames.alert_unreach,
            }.get(event.state)
            return None if icon is None else cls(icon_name=icon.value, title=_("Host alert"))

        if event.type.endswith("ALERT HANDLER STARTED"):
            return cls(
                icon_name=IconNames.alert_alert_handler_started.value,
                title=_("Alert handler started"),
            )

        if event.type.endswith("ALERT HANDLER STOPPED"):
            if event.state == 0:
                return cls(
                    icon_name=IconNames.alert_alert_handler_stopped.value,
                    title=_("Alert handler stopped"),
                )
            return cls(
                icon_name=IconNames.alert_alert_handler_failed.value,
                title=_("Alert handler failed"),
            )

        if "DOWNTIME" in event.type:
            if event.state_type in ("END", "STOPPED"):
                return cls(
                    icon_name=IconNames.alert_downtimestop.value, title=_("Downtime stopped")
                )
            return cls(icon_name=IconNames.alert_downtime.value, title=_("Downtime"))

        if event.type.endswith("NOTIFICATION"):
            if event.command_name == "check-mk-notify":
                return cls(
                    icon_name=IconNames.alert_cmk_notify.value,
                    title=_("Core produced a notification"),
                )
            return cls(icon_name=IconNames.alert_notify.value, title=_("User notification"))

        if event.type.endswith("NOTIFICATION RESULT"):
            return cls(
                icon_name=IconNames.alert_notify_result.value, title=_("Final notification result")
            )

        if event.type.endswith("NOTIFICATION PROGRESS"):
            return cls(
                icon_name=IconNames.alert_notify_progress.value,
                title=_("The notification is being processed"),
            )

        if event.type == "EXTERNAL COMMAND":
            return cls(icon_name=IconNames.alert_command.value, title=_("External command"))

        if "restarting..." in event.type:
            return cls(icon_name=IconNames.alert_restart.value, title=_("Core restarted"))

        if "Reloading configuration" in event.type:
            return cls(
                icon_name=IconNames.alert_reload.value, title=_("Core configuration reloaded")
            )

        if "starting..." in event.type:
            return cls(icon_name=IconNames.alert_start.value, title=_("Core started"))

        if "shutdown..." in event.type or "shutting down" in event.type:
            return cls(icon_name=IconNames.alert_stop.value, title=_("Core stopped"))

        if " FLAPPING " in event.type:
            return cls(icon_name=IconNames.alert_flapping.value, title=_("Flapping"))

        if "ACKNOWLEDGE ALERT" in event.type:
            if event.state_type == "STARTED":
                return cls(icon_name=IconNames.alert_ack.value, title=_("Acknowledged"))
            return cls(icon_name=IconNames.alert_ackstop.value, title=_("Stopped acknowledgment"))

        return None

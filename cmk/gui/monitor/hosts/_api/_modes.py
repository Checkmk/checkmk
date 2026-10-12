#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum

from cmk.gui.i18n import _, ungettext
from cmk.gui.openapi.framework.model import api_field, api_model

from .._models import Host
from ._urls import host_view_link


class HostModeId(enum.StrEnum):
    DOWNTIME = "downtime"
    ACKNOWLEDGED = "acknowledged"
    NOTIFICATIONS_OFF = "notifications_off"
    COMMENTS = "comments"
    ACTIVE_CHECKS_OFF = "active_checks_off"
    PASSIVE_CHECKS_OFF = "passive_checks_off"
    OUT_OF_NOTIFICATION_PERIOD = "out_of_notification_period"
    OUT_OF_SERVICE_PERIOD = "out_of_service_period"
    NOT_CHECKED = "not_checked"


@api_model
class ModeInfo:
    id: HostModeId = api_field(
        description="Stable, untranslated identifier of the mode", example="downtime"
    )
    icon_name: str = api_field(description="Icon to render for this mode", example="downtime")
    link: str = api_field(
        description="URL the mode icon links to, empty for a mode without a view of its own",
        example="view.py?view_name=downtimes_of_host&host=web-server-01",
    )
    title: str = api_field(
        description="Tooltip shown for the mode icon", example="In scheduled downtime"
    )


def build_host_modes(host: Host) -> list[ModeInfo]:
    modes: list[ModeInfo] = []
    if host.in_downtime:
        modes.append(
            ModeInfo(
                id=HostModeId.DOWNTIME,
                icon_name="downtime",
                link=host_view_link("downtimes_of_host", host),
                title=_("In scheduled downtime"),
            )
        )
    if host.acknowledged:
        modes.append(
            ModeInfo(
                id=HostModeId.ACKNOWLEDGED,
                icon_name="ack",
                link="",
                title=_("Problem acknowledged"),
            )
        )
    if not host.notifications_enabled:
        modes.append(
            ModeInfo(
                id=HostModeId.NOTIFICATIONS_OFF,
                icon_name="notif-disabled",
                link="",
                title=_("Notifications are disabled for this host"),
            )
        )
    if host.num_comments:
        modes.append(
            ModeInfo(
                id=HostModeId.COMMENTS,
                icon_name="comment",
                link=host_view_link("comments_of_host", host),
                title=ungettext(
                    "This host has %(count)d comment",
                    "This host has %(count)d comments",
                    host.num_comments,
                )
                % {"count": host.num_comments},
            )
        )
    if host.active_checks_disabled:
        modes.append(
            ModeInfo(
                id=HostModeId.ACTIVE_CHECKS_OFF,
                icon_name="disabled",
                link="",
                title=_("Active checks have been manually disabled for this host"),
            )
        )
    if host.passive_checks_disabled:
        modes.append(
            ModeInfo(
                id=HostModeId.PASSIVE_CHECKS_OFF,
                icon_name="npassive",
                link="",
                title=_("Passive checks have been manually disabled for this host"),
            )
        )
    if not host.in_notification_period:
        modes.append(
            ModeInfo(
                id=HostModeId.OUT_OF_NOTIFICATION_PERIOD,
                icon_name="outofnot",
                link="",
                title=_("Out of notification period"),
            )
        )
    if not host.in_service_period:
        modes.append(
            ModeInfo(
                id=HostModeId.OUT_OF_SERVICE_PERIOD,
                icon_name="outof-serviceperiod",
                link="",
                title=_("Out of service period"),
            )
        )
    if not host.in_check_period:
        modes.append(
            ModeInfo(
                id=HostModeId.NOT_CHECKED,
                icon_name="pause",
                link="",
                title=_("This host is currently not being checked"),
            )
        )
    return modes

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.i18n import _, ungettext
from cmk.gui.openapi.framework.model import api_field, api_model

from .._models import Host
from ._urls import host_panel_link, host_view_link


@api_model
class ModeInfo:
    icon_name: str = api_field(description="Icon to render for this mode", example="downtime")
    link: str = api_field(
        description="URL the mode icon links to",
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
                icon_name="downtime",
                link=host_view_link("downtimes_of_host", host),
                title=_("In scheduled downtime"),
            )
        )
    if host.acknowledged:
        modes.append(
            ModeInfo(
                icon_name="ack",
                link=host_panel_link(host),
                title=_("Problem acknowledged"),
            )
        )
    if not host.notifications_enabled:
        modes.append(
            ModeInfo(
                icon_name="notif-disabled",
                link=host_panel_link(host),
                title=_("Notifications are disabled for this host"),
            )
        )
    if host.num_comments:
        modes.append(
            ModeInfo(
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
                icon_name="disabled",
                link=host_panel_link(host),
                title=_("Active checks have been manually disabled for this host"),
            )
        )
    if host.passive_checks_disabled:
        modes.append(
            ModeInfo(
                icon_name="npassive",
                link=host_panel_link(host),
                title=_("Passive checks have been manually disabled for this host"),
            )
        )
    if not host.in_notification_period:
        modes.append(
            ModeInfo(
                icon_name="outofnot",
                link=host_panel_link(host),
                title=_("Out of notification period"),
            )
        )
    if not host.in_service_period:
        modes.append(
            ModeInfo(
                icon_name="outof-serviceperiod",
                link=host_panel_link(host),
                title=_("Out of service period"),
            )
        )
    if not host.in_check_period:
        modes.append(
            ModeInfo(
                icon_name="pause",
                link=host_panel_link(host),
                title=_("This host is currently not being checked"),
            )
        )
    return modes

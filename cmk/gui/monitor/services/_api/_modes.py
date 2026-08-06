#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.i18n import _
from cmk.gui.openapi.framework.model._api_field import api_field
from cmk.gui.openapi.framework.model._api_model import api_model

from .._models import ServiceOverview
from ._urls import service_view_link


@api_model
class ServiceModeInfo:
    icon_name: str = api_field(description="Icon to render for this mode", example="downtime")
    link: str = api_field(
        description="URL the mode icon links to",
        example="view.py?view_name=downtimes_of_service&host=web-server-01&service=CPU+load",
    )
    title: str = api_field(
        description="Tooltip shown for the mode icon", example="In scheduled downtime"
    )


def build_service_modes(service: ServiceOverview) -> list[ServiceModeInfo]:
    modes: list[ServiceModeInfo] = []
    if service.in_downtime:
        modes.append(
            ServiceModeInfo(
                icon_name="downtime",
                link=service_view_link("downtimes_of_service", service),
                title=_("In scheduled downtime"),
            )
        )
    if service.acknowledged:
        modes.append(
            ServiceModeInfo(
                icon_name="ack",
                link=service_view_link("service", service),
                title=_("Problem acknowledged"),
            )
        )
    if not service.notifications_enabled:
        modes.append(
            ServiceModeInfo(
                icon_name="notif_disabled",
                link=service_view_link("service", service),
                title=_("Notifications are disabled for this service"),
            )
        )
    return modes

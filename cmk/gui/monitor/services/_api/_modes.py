#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.i18n import _
from cmk.gui.openapi.framework.model import api_field, api_model

from .._models import Service, ServiceOverview
from ._urls import host_view_link, service_view_link, service_view_link_by_id

# NOTE: named with a "Service" prefix (unlike the shape-identical hosts ``ModeInfo``) because the
# OpenAPI spec registers component schemas by class name across every endpoint family; an
# unprefixed name would collide with the hosts model.


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
    """Modes shown in the slide-in header; flapping is excluded, it has its own state badge."""
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
                icon_name="notif-disabled",
                link=service_view_link("service", service),
                title=_("Notifications are disabled for this service"),
            )
        )
    return modes


def build_service_modes_by_id(
    service: Service, *, hostname: str, site_id: str
) -> list[ServiceModeInfo]:
    """Modes shown in the Mode column; flapping is excluded, it has its own state-column badge."""
    modes: list[ServiceModeInfo] = []
    if service.in_downtime:
        modes.append(
            ServiceModeInfo(
                icon_name="downtime",
                link=service_view_link_by_id(
                    "downtimes_of_service",
                    site_id=site_id,
                    hostname=hostname,
                    service_name=service.name,
                ),
                title=_("In scheduled downtime"),
            )
        )
    if service.acknowledged:
        modes.append(
            ServiceModeInfo(
                icon_name="ack",
                link=service_view_link_by_id(
                    "service", site_id=site_id, hostname=hostname, service_name=service.name
                ),
                title=_("Problem acknowledged"),
            )
        )
    if not service.notifications_enabled:
        modes.append(
            ServiceModeInfo(
                icon_name="notif-disabled",
                link=service_view_link_by_id(
                    "service", site_id=site_id, hostname=hostname, service_name=service.name
                ),
                title=_("Notifications are disabled for this service"),
            )
        )
    return modes


def build_host_modes(service: ServiceOverview) -> list[ServiceModeInfo]:
    """Modes of the host the service runs on, shown next to the host in the overview."""
    modes: list[ServiceModeInfo] = []
    if service.host_in_downtime:
        modes.append(
            ServiceModeInfo(
                icon_name="downtime",
                link=host_view_link("downtimes_of_host", service),
                title=_("Host is in scheduled downtime"),
            )
        )
    if service.host_acknowledged:
        modes.append(
            ServiceModeInfo(
                icon_name="ack",
                link=host_view_link("host", service),
                title=_("Host problem acknowledged"),
            )
        )
    return modes

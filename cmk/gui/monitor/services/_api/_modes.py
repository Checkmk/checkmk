#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.model import api_field, api_model

from .._models import Service, ServiceOverview
from ._urls import (
    crash_report_link,
    host_panel_link,
    host_view_link,
    service_panel_link,
    service_panel_link_by_id,
    service_view_link,
    service_view_link_by_id,
)

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


def _comment_title(count: int) -> str:
    return ungettext(
        "This service has %(count)d comment",
        "This service has %(count)d comments",
        count,
    ) % {"count": count}


def _crashed_check_mode(service: Service, *, site_id: str) -> ServiceModeInfo:
    """The crash icon, as much of it as the viewer is allowed to see.

    Reading a crash dump needs a permission most users do not have, so without it the icon only
    says the check crashed and links nowhere. A dump the check was too early to write leaves the
    icon linkless too.
    """
    if not user.may("general.see_crash_reports"):
        return ServiceModeInfo(
            icon_name="crash",
            link="",
            title=_(
                "This check crashed. Please inform a Checkmk user that is allowed to view and "
                "submit crash reports to the development team."
            ),
        )
    if (crash_id := service.crash_id) is None:
        return ServiceModeInfo(
            icon_name="crash",
            link="",
            title=_(
                "This check crashed, but no crash dump is available, please report this to the "
                "development team."
            ),
        )
    return ServiceModeInfo(
        icon_name="crash",
        link=crash_report_link(site_id=site_id, crash_id=crash_id),
        title=_(
            "This check crashed. Please click here for more information. You can also submit a "
            "crash report to the development team if you like."
        ),
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
                link=service_panel_link(service),
                title=_("Problem acknowledged"),
            )
        )
    if not service.notifications_enabled:
        modes.append(
            ServiceModeInfo(
                icon_name="notif-disabled",
                link=service_panel_link(service),
                title=_("Notifications are disabled for this service"),
            )
        )
    if service.num_comments:
        modes.append(
            ServiceModeInfo(
                icon_name="comment",
                link=service_view_link("comments_of_service", service),
                title=_comment_title(service.num_comments),
            )
        )
    if service.active_checks_disabled:
        modes.append(
            ServiceModeInfo(
                icon_name="disabled",
                link=service_panel_link(service),
                title=_("Active checks have been manually disabled for this service"),
            )
        )
    if service.passive_checks_disabled:
        modes.append(
            ServiceModeInfo(
                icon_name="npassive",
                link=service_panel_link(service),
                title=_("Passive checks have been manually disabled for this service"),
            )
        )
    if not service.in_notification_period:
        modes.append(
            ServiceModeInfo(
                icon_name="outofnot",
                link=service_panel_link(service),
                title=_("Out of notification period"),
            )
        )
    if not service.in_service_period:
        modes.append(
            ServiceModeInfo(
                icon_name="outof-serviceperiod",
                link=service_panel_link(service),
                title=_("Out of service period"),
            )
        )
    if not service.in_check_period:
        modes.append(
            ServiceModeInfo(
                icon_name="pause",
                link=service_panel_link(service),
                title=_("This service is currently not being checked"),
            )
        )
    if service.check_crashed:
        modes.append(_crashed_check_mode(service, site_id=service.site_id))
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
                link=service_panel_link_by_id(
                    site_id=site_id, hostname=hostname, service_name=service.name
                ),
                title=_("Problem acknowledged"),
            )
        )
    if not service.notifications_enabled:
        modes.append(
            ServiceModeInfo(
                icon_name="notif-disabled",
                link=service_panel_link_by_id(
                    site_id=site_id, hostname=hostname, service_name=service.name
                ),
                title=_("Notifications are disabled for this service"),
            )
        )
    if service.num_comments:
        modes.append(
            ServiceModeInfo(
                icon_name="comment",
                link=service_view_link_by_id(
                    "comments_of_service",
                    site_id=site_id,
                    hostname=hostname,
                    service_name=service.name,
                ),
                title=_comment_title(service.num_comments),
            )
        )
    if service.active_checks_disabled:
        modes.append(
            ServiceModeInfo(
                icon_name="disabled",
                link=service_panel_link_by_id(
                    site_id=site_id, hostname=hostname, service_name=service.name
                ),
                title=_("Active checks have been manually disabled for this service"),
            )
        )
    if service.passive_checks_disabled:
        modes.append(
            ServiceModeInfo(
                icon_name="npassive",
                link=service_panel_link_by_id(
                    site_id=site_id, hostname=hostname, service_name=service.name
                ),
                title=_("Passive checks have been manually disabled for this service"),
            )
        )
    if not service.in_notification_period:
        modes.append(
            ServiceModeInfo(
                icon_name="outofnot",
                link=service_panel_link_by_id(
                    site_id=site_id, hostname=hostname, service_name=service.name
                ),
                title=_("Out of notification period"),
            )
        )
    if not service.in_service_period:
        modes.append(
            ServiceModeInfo(
                icon_name="outof-serviceperiod",
                link=service_panel_link_by_id(
                    site_id=site_id, hostname=hostname, service_name=service.name
                ),
                title=_("Out of service period"),
            )
        )
    if not service.in_check_period:
        modes.append(
            ServiceModeInfo(
                icon_name="pause",
                link=service_panel_link_by_id(
                    site_id=site_id, hostname=hostname, service_name=service.name
                ),
                title=_("This service is currently not being checked"),
            )
        )
    if service.check_crashed:
        modes.append(_crashed_check_mode(service, site_id=site_id))
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
                link=host_panel_link(service),
                title=_("Host problem acknowledged"),
            )
        )
    return modes

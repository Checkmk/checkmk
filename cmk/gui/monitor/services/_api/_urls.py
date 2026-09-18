#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from urllib.parse import urlencode

from cmk.gui.logged_in import user
from cmk.gui.monitor.hosts._api._urls import host_panel_link_by_id

from .._models import ServiceOverview

_HOST_SERVICES_PERMISSION = "view.host"

_SERVICE_STATUS_VIEW_NAME = "service"


def service_view_link(view_name: str, service: ServiceOverview) -> str:
    return "view.py?" + urlencode(
        [
            ("view_name", view_name),
            ("site", service.site_id),
            ("host", service.host_name),
            ("service", service.name),
        ]
    )


def service_view_link_by_id(
    view_name: str, *, site_id: str, hostname: str, service_name: str
) -> str:
    return "view.py?" + urlencode(
        [
            ("view_name", view_name),
            ("site", site_id),
            ("host", hostname),
            ("service", service_name),
        ]
    )


def service_panel_link(service: ServiceOverview) -> str:
    return service_panel_link_by_id(
        site_id=service.site_id, hostname=service.host_name, service_name=service.name
    )


def service_panel_link_by_id(*, site_id: str, hostname: str, service_name: str) -> str:
    """The services listing with this service's panel open, named the way the listing writes it.

    A user who may not see that listing keeps the classic service status view.
    """
    if not user.may(_HOST_SERVICES_PERMISSION):
        return service_view_link_by_id(
            _SERVICE_STATUS_VIEW_NAME,
            site_id=site_id,
            hostname=hostname,
            service_name=service_name,
        )
    page = "monitor_host_services.py?" + urlencode([("host", hostname), ("site", site_id)])
    return f"{page}#" + urlencode([("service", service_name)])


def host_panel_link(service: ServiceOverview) -> str:
    """The all hosts listing with this service's host panel open."""
    return host_panel_link_by_id(site_id=service.site_id, hostname=service.host_name)


def service_parameters_link(service: ServiceOverview) -> str:
    return "wato.py?" + urlencode(
        [
            ("mode", "object_parameters"),
            ("host", service.host_name),
            ("service", service.name),
        ]
    )


def host_view_link(view_name: str, service: ServiceOverview) -> str:
    return "view.py?" + urlencode(
        [
            ("view_name", view_name),
            ("site", service.site_id),
            ("host", service.host_name),
        ]
    )


def crash_report_link(*, site_id: str, crash_id: str) -> str:
    return "crash.py?" + urlencode([("site", site_id), ("crash_id", crash_id)])

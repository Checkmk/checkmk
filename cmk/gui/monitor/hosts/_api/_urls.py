#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from urllib.parse import urlencode

from cmk.gui.logged_in import user

from .._models import Host

_ALL_HOSTS_PERMISSION = "view.allhosts"

_HOST_STATUS_VIEW_NAME = "hoststatus"


def host_view_link(view_name: str, host: Host) -> str:
    return "view.py?" + urlencode(
        [
            ("view_name", view_name),
            ("site", host.site_id),
            ("host", host.name),
        ]
    )


def host_view_link_by_id(view_name: str, *, site_id: str, hostname: str) -> str:
    return "view.py?" + urlencode(
        [
            ("view_name", view_name),
            ("site", site_id),
            ("host", hostname),
        ]
    )


def host_panel_link(host: Host) -> str:
    return host_panel_link_by_id(site_id=host.site_id, hostname=host.name)


def host_panel_link_by_id(*, site_id: str, hostname: str) -> str:
    """The all hosts listing with this host's panel open, named the way the listing writes it.

    A user who may not see that listing keeps the classic host status view.
    """
    if not user.may(_ALL_HOSTS_PERMISSION):
        return host_view_link_by_id(_HOST_STATUS_VIEW_NAME, site_id=site_id, hostname=hostname)
    return "monitor_all_hosts.py#" + urlencode([("host", hostname), ("site", site_id)])


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

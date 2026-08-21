#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from urllib.parse import urlencode

from .._models import Host


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

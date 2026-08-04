#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict

from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.utils.urls import makeuri_contextless
from cmk.shared_typing.monitoring.page_link_button import MonitoringPageLinkButton

_LEGACY_VIEW_NAME = "host"


def show_host_services_link_button(view_name: str) -> None:
    if view_name != _LEGACY_VIEW_NAME:
        return
    if not (host_name := request.var("host")) or not (site_id := request.var("site")):
        return
    html.vue_component(
        "cmk-monitoring-page-link-button",
        data=asdict(
            MonitoringPageLinkButton(
                url=makeuri_contextless(
                    request,
                    [("host", host_name), ("site", site_id)],
                    filename="monitor_host_services.py",
                ),
                title=_('Try the new "Services of host" view'),
            )
        ),
    )

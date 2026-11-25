#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.http import Request
from cmk.gui.monitor.services.page_url import host_service_panel_url, host_services_url
from cmk.gui.search.livestatus_links import ResultGroup, ResultHost, ResultService, ResultTarget


def monitor_result_url(request: Request, target: ResultTarget) -> str | None:
    """Links a monitoring result of the global search to the monitoring page that shows it

    A host or a service opens Services of its host, as pressing Enter does for a single host.
    Groups have no page yet, so the global search keeps their classic view.
    """
    match target:
        case ResultHost(site_id=site_id, host_name=host_name):
            return host_services_url(
                request, host_name=host_name, site_id=site_id, open_host_panel=True
            )
        case ResultService(site_id=site_id, host_name=host_name, service=service):
            return host_service_panel_url(
                request, host_name=host_name, site_id=site_id, service=service
            )
        case ResultGroup():
            return None

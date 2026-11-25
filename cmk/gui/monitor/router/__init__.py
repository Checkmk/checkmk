#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The ``monitor_search.py`` page opens a global search query on the monitoring page for it

* A query without prefix goes to the column filter of the first of host name, alias, address and
  folder title that finds hosts, else to the search box of All hosts.
* A query with host prefixes goes to the column filters of All hosts.
* Either opens Services of host with its host panel instead when it finds a single host.
* A query with service prefixes goes to the column filters of All services.

An invalid query goes to the search box of All hosts as typed. One no page can filter on yet
goes to the legacy search ``search_open.py`` and is logged by its prefixes and the reason.

``monitor_result_url`` links host and service results of the global search to Services of their
host, with the host or service panel open. It returns None for targets no monitoring page shows
yet, such as groups.
"""

from ._page import FirstHosts, FoundHost, MonitorRouterPage, route
from ._result_urls import monitor_result_url

__all__ = ["FirstHosts", "FoundHost", "MonitorRouterPage", "monitor_result_url", "route"]

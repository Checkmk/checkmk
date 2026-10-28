#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The ``monitor_search.py`` page opens a global search query on the monitoring page for it

* A query without prefix goes to the search box of All hosts.
* A query with host prefixes goes to the column filters of All hosts.
* A query with service prefixes goes to the column filters of All services.

An invalid query goes to the search box of All hosts as typed. One no page can filter on yet
goes to the legacy search ``search_open.py`` and is logged by its prefixes and the reason.
"""

from ._page import MonitorRouterPage, route

__all__ = ["MonitorRouterPage", "route"]

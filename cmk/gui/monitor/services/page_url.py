#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.http import Request
from cmk.web.utils.urls import makeuri_contextless

from ._api._filters import SERVICE_FILTER_NODE, ServiceFilterNode


def all_services_url(request: Request, *, filter_node: ServiceFilterNode) -> str:
    """Builds All services with the filter tree applied.

    Raises:
        pydantic.ValidationError: if the filter tree does not validate against the page's filter
            model. Site conditions are checked by the page against its sites, not here.
    """
    filter_json = SERVICE_FILTER_NODE.dump_json(filter_node).decode()
    SERVICE_FILTER_NODE.validate_json(filter_json)
    return makeuri_contextless(
        request, [("filter", filter_json)], filename="monitor_all_services.py"
    )

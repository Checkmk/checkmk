#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.http import Request
from cmk.gui.monitor.shared import FILTER_NODE, FilterNode
from cmk.web.utils.urls import makeuri_contextless


def all_hosts_url(
    request: Request, *, filter_node: FilterNode | None = None, search: str = ""
) -> str:
    """Builds all hosts with the filter tree applied and the text in its search box.

    Raises:
        pydantic.ValidationError: if the filter tree does not validate against the page's filter
            model. Site conditions are checked by the page against its sites, not here.
    """
    vars_ = []
    if filter_node is not None:
        filter_json = FILTER_NODE.dump_json(filter_node).decode()
        # The nodes are plain dataclasses, only reading them back runs the model's validators.
        FILTER_NODE.validate_json(filter_json)
        vars_.append(("filter", filter_json))
    if search:
        vars_.append(("q", search))
    return makeuri_contextless(request, vars_, filename="monitor_all_hosts.py")

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.http import Request
from cmk.gui.monitor.legacy_context import encode_unapplied_filters
from cmk.gui.monitor.shared import encode_filter_node, FILTER_NODE, FilterNode
from cmk.gui.type_defs import FilterName
from cmk.web.utils.urls import makeuri_contextless


def all_hosts_url(
    request: Request,
    *,
    filter_node: FilterNode | None = None,
    search: str = "",
    unapplied: Sequence[FilterName] = (),
) -> str:
    """Builds all hosts with the filter tree applied and the text in its search box. ``unapplied``
    are the legacy filters a link from a legacy view could not take over, for the page to name.

    Raises:
        pydantic.ValidationError: if the filter tree does not validate against the page's filter
            model. Site conditions are checked by the page against its sites, not here.
    """
    vars_ = encode_filter_node(FILTER_NODE, filter_node)
    if search:
        vars_.append(("q", search))
    vars_.extend(encode_unapplied_filters(unapplied))
    return makeuri_contextless(request, vars_, filename="monitor_all_hosts.py")

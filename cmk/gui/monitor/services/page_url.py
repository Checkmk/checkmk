#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from urllib.parse import urlencode

from cmk.gui.http import Request
from cmk.gui.monitor.legacy_context import encode_unapplied_filters
from cmk.gui.type_defs import FilterName
from cmk.web.utils.urls import makeuri_contextless

from ._api._filters import SERVICE_FILTER_NODE, ServiceFilterNode


def _encode_filter(filter_node: ServiceFilterNode | None) -> list[tuple[str, str]]:
    if filter_node is None:
        return []
    filter_json = SERVICE_FILTER_NODE.dump_json(filter_node).decode()
    # The nodes are plain dataclasses, only reading them back runs the model's validators.
    SERVICE_FILTER_NODE.validate_json(filter_json)
    return [("filter", filter_json)]


def all_services_url(
    request: Request,
    *,
    filter_node: ServiceFilterNode | None = None,
    unapplied: Sequence[FilterName] = (),
) -> str:
    """Builds All services with the filter tree applied. ``unapplied`` are the legacy filters a
    link from a legacy view could not take over, for the page to name.

    Raises:
        pydantic.ValidationError: if the filter tree does not validate against the page's filter
            model. Site conditions are checked by the page against its sites, not here.
    """
    return makeuri_contextless(
        request,
        [*_encode_filter(filter_node), *encode_unapplied_filters(unapplied)],
        filename="monitor_all_services.py",
    )


def host_services_url(
    request: Request,
    *,
    host_name: str,
    site_id: str,
    open_host_panel: bool = False,
    filter_node: ServiceFilterNode | None = None,
    unapplied: Sequence[FilterName] = (),
) -> str:
    """Builds Services of host for one host, optionally with its host panel opened and the filter
    tree applied. ``unapplied`` are the legacy filters a link from a legacy view could not take
    over, for the page to name.

    The panel is named in the fragment by the keys HOST_SLIDE_IN in HostServicesApp.vue reads.

    Raises:
        pydantic.ValidationError: if the filter tree does not validate against the page's filter
            model.
    """
    url = makeuri_contextless(
        request,
        [
            ("host", host_name),
            ("site", site_id),
            *_encode_filter(filter_node),
            *encode_unapplied_filters(unapplied),
        ],
        filename="monitor_host_services.py",
    )
    if not open_host_panel:
        return url
    return f"{url}#{urlencode({'host': host_name, 'site': site_id})}"

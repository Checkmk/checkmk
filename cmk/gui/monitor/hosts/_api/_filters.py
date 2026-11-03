#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping

from cmk.gui.monitor.shared import (
    AndNode,
    FilterNode,
    livestatus_filter_lines,
    NotNode,
    OrNode,
    SiteChoiceCondition,
)
from cmk.gui.monitor.site_scope import SiteScopedFilter as GenericSiteScopedFilter
from cmk.gui.monitor.site_scope import SiteScopeExtractor

from .._models import HostFilter

SiteScopedFilter = GenericSiteScopedFilter[FilterNode]


_SITE_SCOPE: SiteScopeExtractor[FilterNode] = SiteScopeExtractor(
    site_condition=SiteChoiceCondition,
    and_node=AndNode,
    or_node=OrNode,
    not_node=NotNode,
    make_and=lambda children: AndNode(type="and", children=children),
)


def scope_filter_by_site(node: FilterNode) -> SiteScopedFilter:
    """Split off the tree's 'site_id' condition, see `SiteScopeExtractor`."""
    return _SITE_SCOPE.scope(node)


def _no_folders() -> Mapping[str, str]:
    return {}


def parse_as_livestatus_filter(
    node: FilterNode, *, setup_folders: Callable[[], Mapping[str, str]] = _no_folders
) -> HostFilter:
    """Render the filter tree as Livestatus filter lines.

    A folder condition is matched against the titles Setup gives its folders, which Livestatus does
    not know, so those are passed in. They arrive as a callable because reading them is not free:
    only a tree that actually carries a folder condition asks for them. Without them no folder has
    a title, and a folder condition selects nothing.
    """
    return HostFilter("\n".join(livestatus_filter_lines(node, setup_folders=setup_folders)))

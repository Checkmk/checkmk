#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.type_defs import ContextualLinkEntryConfig, ViewSpec, VisualName
from cmk.gui.visual_link import may_add_site_hint
from cmk.gui.visuals.info import visual_info_registry

from .type_defs import (
    ContextFilterConfig,
    ContextualLinkCustomConfig,
    ContextualLinkInheritedConfig,
    ContextualLinkTargetType,
)


def contextual_link_from_legacy_target(
    target: tuple[ContextualLinkTargetType, VisualName],
) -> ContextualLinkInheritedConfig:
    """The stored link that replaces a widget's legacy link to a view or a dashboard whose single
    objects are not known, carrying the clicked host's site and name."""
    return ContextualLinkInheritedConfig(
        type="inherited",
        location=target,
        include_context=False,
        include_time_range=False,
        show_filter_form=False,
    )


def contextual_link_from_legacy_view(view: ViewSpec) -> ContextualLinkCustomConfig:
    """The stored link that replaces a widget's legacy link to a view, carrying from the clicked
    host what the legacy link carried: its name only for a view of single hosts, and its site
    where that link added it as a hint."""
    host_filters = ["host"] if "host" in view["single_infos"] else []
    site_filters = (
        ["siteopt"]
        if may_add_site_hint(
            view["name"],
            info_keys=tuple(visual_info_registry.keys()),
            single_info_keys=tuple(view["single_infos"]),
            filter_names=tuple(host_filters),
        )
        else []
    )
    return ContextualLinkCustomConfig(
        type="custom",
        links=[
            ContextualLinkEntryConfig(
                title=str(view["title"]),
                location=("views", view["name"]),
                filters=[
                    ContextFilterConfig(filter_id=filter_id)
                    for filter_id in site_filters + host_filters
                ],
                include_context=False,
                include_time_range=False,
                show_filter_form=False,
            )
        ],
    )

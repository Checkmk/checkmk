#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.type_defs import VisualName

from .type_defs import ContextualLinkInheritedConfig, ContextualLinkTargetType


def contextual_link_from_legacy_target(
    target: tuple[ContextualLinkTargetType, VisualName],
) -> ContextualLinkInheritedConfig:
    """The stored link that replaces a widget's legacy link to a view or a dashboard."""
    # TODO(CMK-39160): answer a custom link with the filters that url_to_visual carries for this
    # target, and create it also for a target outside the permitted visuals.
    return ContextualLinkInheritedConfig(
        type="inherited",
        location=target,
        include_context=False,
        include_time_range=False,
        show_filter_form=False,
    )

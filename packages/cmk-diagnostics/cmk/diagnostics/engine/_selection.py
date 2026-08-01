#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Resolving a topic threshold selection to plug-in names"""

from collections.abc import Iterable, Mapping

from cmk.diagnostics.internal import DiagnosticsPlugin, Sensitivity, Topic


def resolve_selection(
    plugins: Iterable[DiagnosticsPlugin],
    thresholds: Mapping[Topic, Sensitivity | None],
) -> list[str]:
    """Resolve per-topic sensitivity thresholds to the selected plug-in names

    A plug-in is selected iff its topic's threshold is set and its sensitivity
    does not exceed that threshold. Plug-ins collected always are excluded;
    they need no selection. The result is sorted.
    """
    return sorted(
        plugin.name
        for plugin in plugins
        if not plugin.always
        and (threshold := thresholds.get(plugin.topic)) is not None
        and plugin.sensitivity <= threshold
    )

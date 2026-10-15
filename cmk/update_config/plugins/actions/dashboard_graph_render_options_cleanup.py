#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override

import cmk.utils.paths
from cmk.ccc import store
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.plugins.lib.user_profiles import user_directories
from cmk.update_config.registry import update_action_registry

_OBSOLETE_RENDER_OPTIONS = frozenset({"color_gradient", "font_size"})


def _as_dict(value: object, what: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"expected {what} to be a dict, got {value!r}")
    return value


def _strip_widget(widget: object) -> dict[str, object]:
    parsed = _as_dict(widget, "a widget")
    if "graph_render_options" not in parsed:
        return parsed
    render_options = _as_dict(parsed["graph_render_options"], "the graph render options")
    return parsed | {
        "graph_render_options": {
            key: value
            for key, value in render_options.items()
            if key not in _OBSOLETE_RENDER_OPTIONS
        }
    }


def _strip_dashboard(dashboard: object) -> dict[str, object]:
    parsed = _as_dict(dashboard, "a dashboard")
    widgets = _as_dict(parsed["widgets"], "the widgets of a dashboard")
    return parsed | {
        "widgets": {widget_id: _strip_widget(widget) for widget_id, widget in widgets.items()}
    }


def _without_obsolete_render_options(dashboards: dict[str, object]) -> dict[str, object]:
    return {name: _strip_dashboard(dashboard) for name, dashboard in dashboards.items()}


class RemoveObsoleteDashboardGraphRenderOptions(UpdateAction):
    """Drop the render options nothing reads any more from the stored graph widgets."""

    @override
    def __call__(self, logger: Logger) -> None:
        self.remove_obsolete_render_options(cmk.utils.paths.profile_dir, logger)

    @staticmethod
    def remove_obsolete_render_options(profile_dir: Path, logger: Logger) -> None:
        cleaned = 0
        for user_dir in user_directories(profile_dir):
            path = user_dir / "user_dashboards.mk"
            dashboards = store.load_object_from_file(path, default={})
            try:
                stripped = _without_obsolete_render_options(_as_dict(dashboards, "the dashboards"))
            except (TypeError, KeyError) as exc:
                raise ValueError(f"Unexpected format in {path}: {exc}") from exc

            if changed := sum(1 for name, board in dashboards.items() if stripped[name] != board):
                store.save_object_to_file(path, stripped)
                cleaned += changed

        if cleaned:
            logger.info(
                "Removed obsolete graph render options from %(count)d dashboards",
                {"count": cleaned},
            )


update_action_registry.register(
    RemoveObsoleteDashboardGraphRenderOptions(
        name="remove_obsolete_dashboard_graph_render_options",
        title="Remove the obsolete render options of graph widgets",
        sort_index=101,  # no ordering constraints
        expiry_version=ExpiryVersion.CMK_310,
    )
)

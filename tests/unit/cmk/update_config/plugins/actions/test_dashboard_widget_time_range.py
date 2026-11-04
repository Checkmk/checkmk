#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from ast import literal_eval
from collections.abc import Mapping
from pathlib import Path

import pytest

from cmk.update_config.plugins.actions.dashboard_widget_time_range import (
    MigrateDashboardWidgetTimeRange,
)

LOGGER = logging.getLogger()


def _write_dashboards(user_dir: Path, dashboards: Mapping[str, object]) -> Path:
    # save_user_file() writes repr() of the value, which is what the action reads back.
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / "user_dashboards.mk"
    path.write_text(f"{dashboards!r}\n")
    return path


def _widgets(path: Path) -> dict[str, dict[str, object]]:
    widgets: dict[str, dict[str, object]] = literal_eval(path.read_text())["d"]["widgets"]
    return widgets


def test_a_graph_that_followed_time_range_changes_inherits(tmp_path: Path) -> None:
    path = _write_dashboards(
        tmp_path / "cmkadmin",
        {
            "d": {
                "widgets": {
                    "w": {
                        "type": "pnpgraph",
                        "timerange": "35d",
                        "graph_render_options": {"fixed_timerange": False},
                    }
                }
            }
        },
    )

    MigrateDashboardWidgetTimeRange.migrate_time_ranges(tmp_path, LOGGER)

    assert _widgets(path)["w"] == {
        "type": "pnpgraph",
        "timerange": {"type": "dashboard"},
        "graph_render_options": {},
    }


def test_a_graph_that_did_not_follow_time_range_changes_overrides(tmp_path: Path) -> None:
    path = _write_dashboards(
        tmp_path / "cmkadmin",
        {
            "d": {
                "widgets": {
                    "w": {
                        "type": "combined_graph",
                        "timerange": ("age", 7200),
                        "graph_render_options": {"fixed_timerange": True, "show_legend": True},
                    }
                }
            }
        },
    )

    MigrateDashboardWidgetTimeRange.migrate_time_ranges(tmp_path, LOGGER)

    assert _widgets(path)["w"] == {
        "type": "combined_graph",
        "timerange": {"type": "range", "window": ("age", 7200)},
        "graph_render_options": {"show_legend": True},
    }


def test_a_scatterplot_inherits(tmp_path: Path) -> None:
    path = _write_dashboards(
        tmp_path / "cmkadmin",
        {"d": {"widgets": {"w": {"type": "average_scatterplot", "time_range": "d0"}}}},
    )

    MigrateDashboardWidgetTimeRange.migrate_time_ranges(tmp_path, LOGGER)

    assert _widgets(path)["w"]["time_range"] == {"type": "dashboard"}


def test_a_widget_listed_as_dashlet_is_migrated(tmp_path: Path) -> None:
    path = _write_dashboards(
        tmp_path / "cmkadmin",
        {"d": {"dashlets": [{"type": "average_scatterplot", "time_range": "25h"}]}},
    )

    MigrateDashboardWidgetTimeRange.migrate_time_ranges(tmp_path, LOGGER)

    dashlets = literal_eval(path.read_text())["d"]["dashlets"]
    assert dashlets == [{"type": "average_scatterplot", "time_range": {"type": "dashboard"}}]


def test_a_dashboard_without_a_time_range_to_migrate_is_not_rewritten(tmp_path: Path) -> None:
    path = _write_dashboards(
        tmp_path / "cmkadmin",
        {
            "d": {
                "widgets": {
                    "w": {
                        "type": "custom_graph",
                        "timerange": {"type": "range", "window": "25h"},
                        "graph_render_options": {},
                    },
                    "x": {"type": "alert_overview", "time_range": ("age", 3600)},
                }
            }
        },
    )
    untouched_content = path.read_text()

    MigrateDashboardWidgetTimeRange.migrate_time_ranges(tmp_path, LOGGER)

    assert path.read_text() == untouched_content


def test_the_count_is_dashboards_not_users(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write_dashboards(
        tmp_path / "cmkadmin",
        {
            "first": {"widgets": {"w": {"type": "average_scatterplot", "time_range": "4h"}}},
            "second": {"widgets": {"w": {"type": "average_scatterplot", "time_range": "8d"}}},
        },
    )

    with caplog.at_level(logging.INFO):
        MigrateDashboardWidgetTimeRange.migrate_time_ranges(tmp_path, LOGGER)

    assert "2 dashboards" in caplog.text


def test_a_widget_without_a_type_is_reported(tmp_path: Path) -> None:
    _write_dashboards(tmp_path / "cmkadmin", {"d": {"widgets": {"w": {"timerange": "25h"}}}})

    with pytest.raises(ValueError, match="user_dashboards.mk"):
        MigrateDashboardWidgetTimeRange.migrate_time_ranges(tmp_path, LOGGER)

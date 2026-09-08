#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from ast import literal_eval
from collections.abc import Mapping
from pathlib import Path

import pytest

from cmk.update_config.plugins.actions.dashboard_graph_font_size_cleanup import (
    RemoveDashboardGraphFontSize,
)

LOGGER = logging.getLogger()


def _write_dashboards(user_dir: Path, dashboards: Mapping[str, object]) -> Path:
    # save_user_file() writes repr() of the value, which is what the action reads back.
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / "user_dashboards.mk"
    path.write_text(f"{dashboards!r}\n")
    return path


def test_remove_font_size(tmp_path: Path) -> None:
    path = _write_dashboards(
        tmp_path / "cmkadmin",
        {
            "my_dashboard": {
                "title": "My dashboard",
                "widgets": {
                    "some-uuid": {
                        "type": "custom_graph",
                        "graph_render_options": {"font_size": 20.0, "show_legend": True},
                    },
                    "other-uuid": {
                        "type": "single_timeseries",
                        "graph_render_options": {"show_legend": False},
                    },
                    "third-uuid": {"type": "state", "title": "no render options at all"},
                },
            }
        },
    )

    RemoveDashboardGraphFontSize.remove_font_size(tmp_path, LOGGER)

    dashboard = literal_eval(path.read_text())["my_dashboard"]
    assert dashboard["title"] == "My dashboard"
    widgets = dashboard["widgets"]
    assert widgets["some-uuid"] == {
        "type": "custom_graph",
        "graph_render_options": {"show_legend": True},
    }
    assert widgets["other-uuid"]["graph_render_options"] == {"show_legend": False}
    assert widgets["third-uuid"] == {"type": "state", "title": "no render options at all"}


def test_remove_font_size_leaves_other_users_alone(tmp_path: Path) -> None:
    """Every user is swept, and only the files that carry the key are rewritten."""
    with_font_size = _write_dashboards(
        tmp_path / "harry",
        {"d": {"widgets": {"w": {"graph_render_options": {"font_size": 12.0}}}}},
    )
    without_font_size = _write_dashboards(
        tmp_path / "hermione",
        {"d": {"widgets": {"w": {"graph_render_options": {"show_legend": True}}}}},
    )
    untouched_content = without_font_size.read_text()

    RemoveDashboardGraphFontSize.remove_font_size(tmp_path, LOGGER)

    rewritten = literal_eval(with_font_size.read_text())
    assert rewritten["d"]["widgets"]["w"]["graph_render_options"] == {}
    assert without_font_size.read_text() == untouched_content


def test_the_count_is_dashboards_not_users(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """One user with two cleaned dashboards must not report as one."""
    _write_dashboards(
        tmp_path / "cmkadmin",
        {
            "first": {"widgets": {"w": {"graph_render_options": {"font_size": 8.0}}}},
            "second": {"widgets": {"w": {"graph_render_options": {"font_size": 20.0}}}},
            "untouched": {"widgets": {"w": {"graph_render_options": {"show_legend": True}}}},
        },
    )

    with caplog.at_level(logging.INFO):
        RemoveDashboardGraphFontSize.remove_font_size(tmp_path, LOGGER)

    assert "2 dashboards" in caplog.text


def test_a_user_without_dashboards_gets_no_file(tmp_path: Path) -> None:
    (tmp_path / "cmkadmin").mkdir()

    RemoveDashboardGraphFontSize.remove_font_size(tmp_path, LOGGER)

    assert not (tmp_path / "cmkadmin" / "user_dashboards.mk").exists()


@pytest.mark.parametrize(
    "dashboards",
    [
        pytest.param({"d": "not a dashboard"}, id="dashboard is not a dict"),
        pytest.param({"d": {"title": "no widgets key"}}, id="dashboard without widgets"),
        pytest.param({"d": {"widgets": ["not a mapping"]}}, id="widgets are not a dict"),
        pytest.param({"d": {"widgets": {"w": "not a widget"}}}, id="widget is not a dict"),
        pytest.param(
            {"d": {"widgets": {"w": {"graph_render_options": 8.0}}}},
            id="render options are not a dict",
        ),
    ],
)
def test_a_dashboard_it_cannot_read_fails_the_action(
    tmp_path: Path, dashboards: Mapping[str, object]
) -> None:
    """Refuse rather than leave the key behind: a half-swept profile is hard to spot later."""
    path = _write_dashboards(tmp_path / "cmkadmin", dashboards)
    content_before = path.read_text()

    with pytest.raises(ValueError, match=str(path)):
        RemoveDashboardGraphFontSize.remove_font_size(tmp_path, LOGGER)

    assert path.read_text() == content_before

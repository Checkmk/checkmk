#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.dashboard import builtin_dashboard_extender_registry, builtin_dashboards


def test_builtin_dashboard_name_matches_id(load_config: Config, test_edition: Edition) -> None:
    assert len(builtin_dashboards) > 0, "There should be at least one built-in dashboard defined"
    extender = builtin_dashboard_extender_registry[str(test_edition)]
    extended_dashboards = extender.callable(builtin_dashboards.copy(), load_config)
    for dashboard_id, dashboard_config in extended_dashboards.items():
        assert dashboard_id == dashboard_config["name"], (
            f"Dashboard ID '{dashboard_id}' does not match its name '{dashboard_config['name']}'"
        )


def test_builtin_dashboards_drill_down_instead_of_linking(
    load_config: Config, test_edition: Edition
) -> None:
    extender = builtin_dashboard_extender_registry[str(test_edition)]
    extended_dashboards = extender.callable(builtin_dashboards.copy(), load_config)

    linked_columns = [
        (dashboard_id, embedded_id, painter.name)
        for dashboard_id, dashboard_config in extended_dashboards.items()
        for embedded_id, embedded_view in dashboard_config["embedded_views"].items()
        for painter in embedded_view["painters"]
        if painter.link_spec is not None
    ]

    assert linked_columns == []

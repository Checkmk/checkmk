#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import cmk.ccc.version as cmk_version
from cmk.gui.config import Config
from cmk.gui.dashboard import builtin_dashboard_extender_registry, builtin_dashboards
from cmk.utils import paths


def test_builtin_dashboard_name_matches_id(load_config: Config) -> None:
    assert len(builtin_dashboards) > 0, "There should be at least one built-in dashboard defined"
    extender = builtin_dashboard_extender_registry[str(cmk_version.edition(paths.omd_root))]
    extended_dashboards = extender.callable(builtin_dashboards.copy(), load_config)
    for dashboard_id, dashboard_config in extended_dashboards.items():
        assert dashboard_id == dashboard_config["name"], (
            f"Dashboard ID '{dashboard_id}' does not match its name '{dashboard_config['name']}'"
        )

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.search.engines.monitoring import ServiceStateMatchPlugin, UsedFilters


class TestServiceStateMatchPlugin:
    @pytest.fixture
    def plugin(self) -> ServiceStateMatchPlugin:
        return ServiceStateMatchPlugin()

    @pytest.mark.parametrize(
        "used_filters, expected",
        [
            pytest.param(
                {"st": ["ok"]},
                "Filter: state = 0",
                id="single value",
            ),
            pytest.param(
                {"st": ["ok", "warn"]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="multiple values",
            ),
            pytest.param(
                {"st": ["ok|warn"]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="with pipe operator",
            ),
            pytest.param(
                {"st": ["ok|warn|crit"]},
                "Filter: state = 0\nFilter: state = 1\nFilter: state = 2\nOr: 3",
                id="with pipe operator multiple pipes",
            ),
            pytest.param(
                {"st": ["(ok|warn)"]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="wrapped in parentheses",
            ),
            pytest.param(
                {"st": ["ok|warn "]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="trailing right whitespace",
            ),
            pytest.param(
                {"st": [" ok|warn"]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="trailing left whitespace",
            ),
            pytest.param(
                {"st": [" ok|warn "]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="left and right whitespace",
            ),
            pytest.param(
                {"st": ["ok | warn"]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="whitespace between operator",
            ),
        ],
    )
    def test_get_livestatus_filters(
        self, plugin: ServiceStateMatchPlugin, used_filters: UsedFilters, expected: str
    ) -> None:
        livestatus_table = plugin.get_preferred_livestatus_table()
        value = plugin.get_livestatus_filters(livestatus_table, used_filters)
        assert value == expected

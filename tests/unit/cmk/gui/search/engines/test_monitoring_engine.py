#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.search.engines.monitoring import (
    FilterBehaviour,
    GroupMatchPlugin,
    HostMatchPlugin,
    LivestatusQuicksearchConductor,
    ServiceStateMatchPlugin,
    UsedFilters,
)


class TestGetSearchUrlParams:
    """The "press Enter" search path (search_open.py) builds its target URL via
    get_search_url_params(). For an exact host match it must carry the matched
    site, otherwise context-dependent page menu entries (e.g. the host inventory)
    are suppressed - see cmk.gui.views.visual_type._compute_link_from_result()."""

    def test_exact_host_match_includes_site(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = "hosts"
        conductor._rows = [{"site": "mysite", "name": "myhost", "host_name": "myhost"}]
        conductor._used_search_plugins = [HostMatchPlugin(livestatus_field="name", name="h")]

        url_params = conductor.get_search_url_params()

        assert ("view_name", "host") in url_params
        assert ("host", "myhost") in url_params
        assert ("site", "mysite") in url_params

    def test_multiple_host_matches_omit_site(self) -> None:
        # Same host name present on two sites -> not an exact match. We navigate to
        # the search view listing both, so no single site may be pinned.
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = "hosts"
        conductor._rows = [
            {"site": "site1", "name": "myhost", "host_name": "myhost"},
            {"site": "site2", "name": "myhost", "host_name": "myhost"},
        ]
        conductor._used_search_plugins = [HostMatchPlugin(livestatus_field="name", name="h")]

        url_params = conductor.get_search_url_params()

        assert ("view_name", "searchhost") in url_params
        assert not any(key == "site" for key, _value in url_params)

    def test_group_match_omits_site(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"hg": ["mygroup"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = "hostgroups"
        conductor._rows = [{"site": "mysite", "name": "mygroup"}]
        conductor._used_search_plugins = [GroupMatchPlugin(group_type="host", name="hg")]

        url_params = conductor.get_search_url_params()

        assert not any(key == "site" for key, _value in url_params)


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

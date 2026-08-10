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
    LivestatusResult,
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


class TestGenerateDisplayTexts:
    @staticmethod
    def _conductor(
        livestatus_table: str, used_filters: UsedFilters | None = None
    ) -> LivestatusQuicksearchConductor:
        conductor = LivestatusQuicksearchConductor(
            used_filters or {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = livestatus_table
        return conductor

    def test_unique_host_addresses_show_the_host_name_as_context(self) -> None:
        conductor = self._conductor("hosts", {"ad": ["10.10.15.20"]})
        elements = [
            LivestatusResult(
                text_tokens=[("ad", "10.10.15.200")],
                url="view.py?a=1",
                row={"name": "myhost", "site": "site1"},
                display_text="",
            ),
            LivestatusResult(
                text_tokens=[("ad", "10.10.15.201")],
                url="view.py?a=2",
                row={"name": "otherhost", "site": "site1"},
                display_text="",
            ),
        ]

        results = conductor._generate_display_texts(elements)

        assert [(result.title, result.url, result.context) for result in results] == [
            ("10.10.15.200", "view.py?a=1", "myhost"),
            ("10.10.15.201", "view.py?a=2", "otherhost"),
        ]

    def test_address_match_titled_by_another_filter_gets_no_context(self) -> None:
        conductor = self._conductor("hosts", {"al": ["My alias"], "ad": ["10.10.15.20"]})
        elements = [
            LivestatusResult(
                text_tokens=[("al", "My alias"), ("ad", "10.10.15.200")],
                url="view.py?a=1",
                row={"name": "myhost", "site": "site1"},
                display_text="",
            )
        ]

        results = conductor._generate_display_texts(elements)

        assert [(result.title, result.context) for result in results] == [("My alias", "")]

    def test_host_named_after_its_address_gets_no_redundant_context(self) -> None:
        conductor = self._conductor("hosts", {"ad": ["10.10.15.20"]})
        elements = [
            LivestatusResult(
                text_tokens=[("ad", "10.10.15.200")],
                url="view.py?a=1",
                row={"name": "10.10.15.200", "site": "site1"},
                display_text="",
            )
        ]

        results = conductor._generate_display_texts(elements)

        assert [result.context for result in results] == [""]

    def test_unique_host_names_have_no_context(self) -> None:
        conductor = self._conductor("hosts")
        elements = [
            LivestatusResult(
                text_tokens=[("h", "myhost")],
                url="view.py?a=1",
                row={"name": "myhost", "site": "site1"},
                display_text="",
            )
        ]

        results = conductor._generate_display_texts(elements)

        assert [(result.title, result.url, result.context) for result in results] == [
            ("myhost", "view.py?a=1", "")
        ]

    def test_service_matched_by_host_address_keeps_the_service_title(self) -> None:
        conductor = self._conductor("services", {"ad": ["10.10.15.20"], "s": ["CPU"]})
        elements = [
            LivestatusResult(
                text_tokens=[("ad", "10.10.15.200"), ("s", "CPU load")],
                url="view.py?a=1",
                row={"description": "CPU load", "host_name": "myhost"},
                display_text="",
            )
        ]

        results = conductor._generate_display_texts(elements)

        assert [(result.title, result.context) for result in results] == [("CPU load", "")]


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

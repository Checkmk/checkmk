#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.sidebar._snapin._search import (
    ABCLabelMatchPlugin,
    FilterBehaviour,
    GroupMatchPlugin,
    HostLabelMatchPlugin,
    HostMatchPlugin,
    LivestatusQuicksearchConductor,
    ServiceLabelMatchPlugin,
)
from cmk.gui.utils.labels import Label


class TestGetSearchUrlParams:
    """The "press Enter" search path builds its target URL via
    get_search_url_params(). For an exact host match it must carry the matched
    site, otherwise context-dependent page menu entries (e.g. the host inventory)
    are suppressed."""

    def test_exact_host_match_includes_site(self) -> None:
        conductor = LivestatusQuicksearchConductor({"h": ["myhost"]}, FilterBehaviour.CONTINUE)
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
        conductor = LivestatusQuicksearchConductor({"h": ["myhost"]}, FilterBehaviour.CONTINUE)
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
        conductor = LivestatusQuicksearchConductor({"hg": ["mygroup"]}, FilterBehaviour.CONTINUE)
        conductor._livestatus_table = "hostgroups"
        conductor._rows = [{"site": "mysite", "name": "mygroup"}]
        conductor._used_search_plugins = [GroupMatchPlugin(group_type="host", name="hg")]

        url_params = conductor.get_search_url_params()

        assert not any(key == "site" for key, _value in url_params)


class TestLabelMatchPlugin:
    def test_input_to_key_value_invalid_ok(self) -> None:
        assert ABCLabelMatchPlugin._input_to_key_value("key:value") == Label("key", "value", False)

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "",
            "abc",
            ":abc",
            "abc:",
        ],
    )
    def test_input_to_key_value_invalid(self, invalid_input: str) -> None:
        with pytest.raises(MKUserError):
            ABCLabelMatchPlugin._input_to_key_value(invalid_input)

    def test_get_livestatus_filters_no_input(self) -> None:
        assert HostLabelMatchPlugin().get_livestatus_filters("", {}) == ""

    def test_get_livestatus_filters_one_filter(self) -> None:
        assert (
            HostLabelMatchPlugin().get_livestatus_filters("hosts", {"hl": ["x:y"]})
            == "Filter: labels = 'x' 'y'"
        )

    def test_get_livestatus_filters_two_filters(self) -> None:
        assert (
            ServiceLabelMatchPlugin().get_livestatus_filters("services", {"sl": ["x:y", "a:b"]})
            == "Filter: labels = 'x' 'y'\nFilter: labels = 'a' 'b'"
        )

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

import pytest

from cmk.gui.search.engines.monitoring import (
    FilterBehaviour,
    FolderMatchPlugin,
    LivestatusQuicksearchConductor,
    Matches,
    QuicksearchManager,
    UsedFilters,
)
from cmk.gui.type_defs import Row


class TestFolderMatchPlugin:
    @pytest.fixture(name="plugin")
    def fixture_plugin(self) -> FolderMatchPlugin:
        return FolderMatchPlugin(livestatus_table="hosts", name="hf")

    def test_match_topic(self, plugin: FolderMatchPlugin) -> None:
        assert plugin.get_match_topic() == "Host folder"

    @pytest.mark.parametrize(
        "livestatus_table, expected",
        [
            pytest.param("hosts", ["filename"], id="hosts carry their file name"),
            pytest.param("services", ["host_filename"], id="services reference the host file"),
        ],
    )
    def test_queried_columns_depend_on_the_table(
        self, plugin: FolderMatchPlugin, livestatus_table: str, expected: list[str]
    ) -> None:
        assert plugin.get_livestatus_columns(livestatus_table) == expected

    @pytest.mark.parametrize(
        "used_filters, expected",
        [
            pytest.param(
                {"hf": ["hamburg"]},
                "Filter: filename ~~ ^/wato/hamburg[^/]*/",
                id="single folder",
            ),
            pytest.param(
                {"hf": ["/hamburg/"]},
                "Filter: filename ~~ ^/wato/hamburg[^/]*/",
                id="surrounding slashes are ignored",
            ),
            pytest.param(
                {"hf": ["hamburg", "berlin"]},
                "Filter: filename ~~ ^/wato/hamburg[^/]*/\n"
                "Filter: filename ~~ ^/wato/berlin[^/]*/\nOr: 2",
                id="several folders are combined with Or",
            ),
            pytest.param({}, "", id="no filter for this plugin yields no headers"),
        ],
    )
    def test_livestatus_filters_are_built(
        self, plugin: FolderMatchPlugin, used_filters: UsedFilters, expected: str
    ) -> None:
        assert plugin.get_livestatus_filters("hosts", used_filters) == expected

    @pytest.mark.parametrize(
        "query, filename, expected",
        [
            pytest.param("hamburg", "/wato/hamburg/hosts.mk", True, id="hosts in the folder"),
            pytest.param("hamburg", "/wato/hamburg/infra/hosts.mk", True, id="hosts in subfolders"),
            pytest.param("hamb", "/wato/hamburg/hosts.mk", True, id="a folder name prefix"),
            pytest.param(
                "hamburg/infra",
                "/wato/hamburg/infrastructure/drucker/hosts.mk",
                True,
                id="a path into the folder tree",
            ),
            pytest.param("HAMBURG", "/wato/hamburg/hosts.mk", True, id="case is ignored"),
            pytest.param(
                "infra", "/wato/hamburg/infra/hosts.mk", False, id="anchored at the main folder"
            ),
            pytest.param("hosts", "/wato/hosts.mk", False, id="main folder hosts are no folder"),
            pytest.param(
                "ham.urg", "/wato/hamburg/hosts.mk", False, id="regex characters are literal"
            ),
            pytest.param("ham*", "/wato/hamburg/hosts.mk", False, id="wildcards are literal"),
            pytest.param("my-site", "/wato/my-site/hosts.mk", True, id="dashes in folder names"),
        ],
    )
    def test_folder_filter_selects_hosts_by_path(
        self, plugin: FolderMatchPlugin, query: str, filename: str, expected: bool
    ) -> None:
        livestatus_regex = plugin.get_livestatus_filters("hosts", {"hf": [query]}).split(" ~~ ")[1]

        assert bool(re.match(livestatus_regex, filename, re.IGNORECASE)) is expected

    def test_a_host_row_links_to_the_host(self, plugin: FolderMatchPlugin) -> None:
        row = {"name": "printer01", "filename": "/wato/hamburg/hosts.mk"}

        matches = plugin.get_matches("host", row, "hosts", {"hf": ["hamburg"]}, [])

        assert matches == ("printer01", [("host", "printer01")])

    def test_a_service_row_links_to_the_service(self, plugin: FolderMatchPlugin) -> None:
        row = {
            "host_name": "printer01",
            "description": "CPU load",
            "host_filename": "/wato/hamburg/infra/hosts.mk",
        }

        matches = plugin.get_matches("allservices", row, "services", {"hf": ["hamburg"]}, [])

        assert matches == ("hamburg/infra", [("host", "printer01"), ("service", "CPU load")])

    @pytest.mark.parametrize(
        "used_filters, expected",
        [
            pytest.param(
                {"hf": ["hamburg"]}, ("hamburg", [("wato_folder", "hamburg*")]), id="a folder"
            ),
            pytest.param(
                {"hf": ["hamb"]}, ("hamb", [("wato_folder", "hamb*")]), id="a folder name prefix"
            ),
            pytest.param(
                {"hf": ["/hamburg/infra/"]},
                ("hamburg/infra", [("wato_folder", "hamburg/infra*")]),
                id="a path",
            ),
            pytest.param(
                {"hf": ["hamburg", "berlin"]},
                ("(hamburg|berlin)", [("wato_folder", "(hamburg|berlin)*")]),
                id="several folders",
            ),
            pytest.param(
                {"hf": ["ham.urg"]},
                ("ham\\.urg", [("wato_folder", "ham\\.urg*")]),
                id="regex characters are escaped",
            ),
        ],
    )
    def test_search_view_is_filtered_by_the_searched_folders(
        self, plugin: FolderMatchPlugin, used_filters: UsedFilters, expected: Matches
    ) -> None:
        rows: list[Row] = [
            {"filename": "/wato/ha/hosts.mk"},
            {"filename": "/wato/hannover/hosts.mk"},
        ]

        assert plugin.get_matches("searchhost", None, "hosts", used_filters, rows) == expected

    def test_unsupported_view_has_no_matches(self, plugin: FolderMatchPlugin) -> None:
        assert plugin.get_matches("hostgroup", None, "hosts", {"hf": ["hamburg"]}, []) is None


class TestServiceFolderMatchPlugin:
    @pytest.fixture(name="plugin")
    def fixture_plugin(self) -> FolderMatchPlugin:
        return FolderMatchPlugin(livestatus_table="services", name="sf")

    def test_match_topic(self, plugin: FolderMatchPlugin) -> None:
        assert plugin.get_match_topic() == "Service folder"

    def test_results_are_services(self, plugin: FolderMatchPlugin) -> None:
        assert plugin.get_preferred_livestatus_table() == "services"

    @pytest.mark.parametrize(
        "livestatus_table, expected",
        [
            pytest.param("services", True, id="services are filtered"),
            pytest.param("hosts", False, id="hosts are not"),
        ],
    )
    def test_only_the_services_table_is_filtered(
        self, plugin: FolderMatchPlugin, livestatus_table: str, expected: bool
    ) -> None:
        assert plugin.is_used_for_table(livestatus_table, {"sf": ["hamburg"]}) is expected

    def test_services_are_selected_by_the_folder_of_their_host(
        self, plugin: FolderMatchPlugin
    ) -> None:
        assert (
            plugin.get_livestatus_filters("services", {"sf": ["hamburg"]})
            == "Filter: host_filename ~~ ^/wato/hamburg[^/]*/"
        )

    def test_search_view_is_filtered_by_the_searched_folder(
        self, plugin: FolderMatchPlugin
    ) -> None:
        assert plugin.get_matches("searchsvc", None, "services", {"sf": ["hamburg"]}, []) == (
            "hamburg",
            [("wato_folder", "hamburg*")],
        )


class TestFolderPrefixes:
    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("hf:hamburg/infra", [("hf:", 0)], id="host folder filter"),
            pytest.param("sf:hamburg/infra", [("sf:", 0)], id="service folder filter"),
        ],
    )
    def test_expressions_are_extracted(self, query: str, expected: list[tuple[str, int]]) -> None:
        assert QuicksearchManager._find_search_object_expressions(query) == expected

    @pytest.mark.parametrize(
        "used_filters, expected",
        [
            pytest.param({"hf": ["hamburg"]}, "hosts", id="host folder"),
            pytest.param({"sf": ["hamburg"]}, "services", id="service folder"),
            pytest.param(
                {"hf": ["hamburg"], "s": ["CPU"]}, "services", id="host folder and service"
            ),
        ],
    )
    def test_table_is_chosen_by_filter_precedence(
        self, used_filters: UsedFilters, expected: str
    ) -> None:
        conductor = LivestatusQuicksearchConductor(
            used_filters, FilterBehaviour.CONTINUE, row_limit=80
        )

        conductor._determine_livestatus_table()

        assert conductor.livestatus_table == expected

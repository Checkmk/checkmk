#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import override

import pytest

from cmk.gui.search.quicksearch import (
    ABCQuicksearchConductor,
    BasicPluginQuicksearchConductor,
    FilterBehaviour,
    LivestatusQuicksearchConductor,
)
from cmk.gui.sidebar._snapin._quicksearch_manager import SnapinQuicksearchManager
from cmk.gui.type_defs import HTTPVariables, SearchResult
from cmk.gui.utils.roles import UserPermissions

USER_PERMISSIONS = UserPermissions({}, {}, {}, [])


def _build_url(addvars: HTTPVariables) -> str:
    return "view.py?" + "&".join(f"{k}={v}" for k, v in addvars)


def _manager(
    *, row_limit: int = 10, search_order: Sequence[tuple[str, str]] = ()
) -> SnapinQuicksearchManager:
    return SnapinQuicksearchManager(
        row_limit=row_limit, search_order=list(search_order), build_url=_build_url
    )


class _FakeConductor(ABCQuicksearchConductor):
    def __init__(self, rows: int, results: list[SearchResult] | None = None) -> None:
        super().__init__({}, FilterBehaviour.CONTINUE, 10)
        self._num_rows = rows
        self._results = results or []

    @override
    def do_query(self) -> None:
        pass

    @override
    def num_rows(self) -> int:
        return self._num_rows

    @override
    def remove_rows_from_end(self, num: int) -> None:
        self._num_rows = max(0, self._num_rows - num)

    @override
    def row_limit_exceeded(self) -> bool:
        return False

    @override
    def get_search_url_params(self) -> HTTPVariables:
        return [("view_name", "searched")]

    @override
    def get_match_topic(self) -> str:
        return "Topic"

    @override
    def create_results(self, build_url: object) -> list[SearchResult]:
        return self._results


@pytest.mark.usefixtures("request_context")
def test_find_search_object_expressions_without_a_filter() -> None:
    assert SnapinQuicksearchManager._find_search_object_expressions("heute") == []


@pytest.mark.usefixtures("request_context")
def test_find_search_object_expressions_at_the_start_of_the_query() -> None:
    assert SnapinQuicksearchManager._find_search_object_expressions("h:heute") == [("h:", 0)]


@pytest.mark.usefixtures("request_context")
def test_find_search_object_expressions_needs_a_word_boundary() -> None:
    """A colon inside a value must not be mistaken for a filter expression, otherwise
    searching for a service like ``Filesystem /h:`` would silently change the search."""
    assert SnapinQuicksearchManager._find_search_object_expressions("myh:heute") == []


@pytest.mark.usefixtures("request_context")
def test_find_search_object_expressions_reports_every_filter_with_its_offset() -> None:
    found = SnapinQuicksearchManager._find_search_object_expressions("h:heute s:CPU")

    assert found == [("h:", 0), (" s:", 7)]


@pytest.mark.usefixtures("request_context")
def test_used_filters_from_a_single_expression() -> None:
    query = "h:heute"

    assert SnapinQuicksearchManager._get_used_filters_from_query(
        query, SnapinQuicksearchManager._find_search_object_expressions(query)
    ) == {"h": ["heute"]}


@pytest.mark.usefixtures("request_context")
def test_used_filters_are_split_at_every_expression() -> None:
    query = "h:heute s:CPU"

    assert SnapinQuicksearchManager._get_used_filters_from_query(
        query, SnapinQuicksearchManager._find_search_object_expressions(query)
    ) == {"h": ["heute"], "s": ["CPU"]}


@pytest.mark.usefixtures("request_context")
def test_used_filters_collect_a_repeated_expression() -> None:
    query = "h:heute h:beta"
    found = SnapinQuicksearchManager._find_search_object_expressions(query)

    assert SnapinQuicksearchManager._get_used_filters_from_query(query, found) == {
        "h": ["beta", "heute"]
    }


@pytest.mark.usefixtures("request_context")
def test_determine_search_objects_uses_one_livestatus_conductor_for_expressions() -> None:
    """An explicit expression addresses exactly one search plug-in, so the configured
    search order is bypassed entirely."""
    search_objects = _manager(search_order=[("h", "continue")]).determine_search_objects(
        "h:heute", USER_PERMISSIONS
    )

    assert len(search_objects) == 1
    assert isinstance(search_objects[0], LivestatusQuicksearchConductor)


@pytest.mark.usefixtures("request_context")
def test_determine_search_objects_follows_the_configured_search_order() -> None:
    search_objects = _manager(
        search_order=[("h", "continue"), ("s", "finished_distinct")]
    ).determine_search_objects("heute", USER_PERMISSIONS)

    assert [o.filter_behaviour for o in search_objects] == [
        FilterBehaviour.CONTINUE,
        FilterBehaviour.FINISHED_DISTINCT,
    ]


@pytest.mark.usefixtures("request_context")
def test_determine_search_objects_without_a_search_order() -> None:
    assert _manager().determine_search_objects("heute", USER_PERMISSIONS) == []


@pytest.mark.usefixtures("request_context")
def test_make_conductor_picks_livestatus_for_a_livestatus_plugin() -> None:
    conductor = _manager()._make_conductor(
        "h", {"h": ["heute"]}, FilterBehaviour.CONTINUE, USER_PERMISSIONS
    )

    assert isinstance(conductor, LivestatusQuicksearchConductor)


@pytest.mark.usefixtures("request_context")
def test_make_conductor_picks_the_basic_conductor_for_other_plugins() -> None:
    conductor = _manager()._make_conductor(
        "menu", {"menu": ["hosts"]}, FilterBehaviour.CONTINUE, USER_PERMISSIONS
    )

    assert isinstance(conductor, BasicPluginQuicksearchConductor)


@pytest.mark.usefixtures("request_context")
def test_generate_search_url_falls_back_to_all_services() -> None:
    """Hitting enter with a query nothing matched must still land on a usable view instead
    of an empty page."""
    url = _manager().generate_search_url("nothing_matches_this", USER_PERMISSIONS)

    assert "view_name=allservices" in url
    assert "service_regex=nothing_matches_this" in url


def test_evaluate_results_skips_conductors_without_results() -> None:
    results = [SearchResult(title="Heute", url="view.py")]

    assert list(_manager().evaluate_results([_FakeConductor(0), _FakeConductor(1, results)])) == [
        ("Topic", results)
    ]


def test_evaluate_results_of_no_conductors() -> None:
    assert list(_manager().evaluate_results([])) == []

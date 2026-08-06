#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

import pytest

from cmk.gui.search.quicksearch import ABCQuicksearchConductor, FilterBehaviour
from cmk.gui.sidebar._snapin._quicksearch_manager import SnapinQuicksearchManager, TooManyRowsError
from cmk.gui.type_defs import HTTPVariables, SearchResult


def test_conduct_search_raises_too_many_rows_error_when_over_limit() -> None:
    engine = SnapinQuicksearchManager(row_limit=2, search_order=[], build_url=_noop_build_url)
    conductor = _FakeConductor(FilterBehaviour.CONTINUE, row_limit=2, rows=5)

    with pytest.raises(TooManyRowsError):
        engine.conduct_search([conductor])

    assert conductor.num_rows() == 2


def test_conduct_search_raises_too_many_rows_error_when_conductor_reports_exceeded() -> None:
    engine = SnapinQuicksearchManager(row_limit=10, search_order=[], build_url=_noop_build_url)
    conductor = _FakeConductor(FilterBehaviour.CONTINUE, row_limit=10, rows=1, exceeded=True)

    with pytest.raises(TooManyRowsError):
        engine.conduct_search([conductor])


def test_conduct_search_finished_distinct_discards_earlier_conductors_rows() -> None:
    engine = SnapinQuicksearchManager(row_limit=10, search_order=[], build_url=_noop_build_url)
    first = _FakeConductor(FilterBehaviour.CONTINUE, row_limit=10, rows=3)
    second = _FakeConductor(FilterBehaviour.FINISHED_DISTINCT, row_limit=10, rows=2)

    engine.conduct_search([first, second])

    assert first.num_rows() == 0


class _FakeConductor(ABCQuicksearchConductor):
    def __init__(
        self,
        filter_behaviour: FilterBehaviour,
        row_limit: int,
        rows: int,
        exceeded: bool = False,
    ) -> None:
        super().__init__({}, filter_behaviour, row_limit)
        self._num_rows = rows
        self._exceeded = exceeded

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
        return self._exceeded

    @override
    def get_search_url_params(self) -> HTTPVariables:
        return []

    @override
    def create_results(self, build_url: object) -> list[SearchResult]:
        return []


def _noop_build_url(addvars: HTTPVariables) -> str:
    return ""

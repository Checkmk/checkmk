#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkers.checkresults import ActiveCheckResult


class TestActiveCheckResult:
    @staticmethod
    def test_as_text_short():
        assert (
            ActiveCheckResult(1, "Make sure this has no trailing newlines and the like").as_text()
            == "Make sure this has no trailing newlines and the like"
        )

    @staticmethod
    def test_as_text_full():
        assert (
            ActiveCheckResult(
                2, "This is the summary", ("Detail: 1", "Detail: 2"), ("detail_count=2",)
            ).as_text()
            == "This is the summary | detail_count=2\nDetail: 1\nDetail: 2"
        )

    @staticmethod
    def test_from_subresults() -> None:
        assert ActiveCheckResult.from_subresults(
            ActiveCheckResult(0, "Ok", ("We're good",), ("metric1",)),
            ActiveCheckResult(2, "Critical", ("We're doomed",), ("metric2",)),
        ) == ActiveCheckResult(
            2, "Ok, Critical(!!)", ("We're good", "We're doomed(!!)"), ("metric1", "metric2")
        )

    @staticmethod
    def test_active_check_result_no_redundant_state_markers() -> None:
        assert ActiveCheckResult.from_subresults(
            ActiveCheckResult.from_subresults(ActiveCheckResult(1, "Be warned")),
        ) == ActiveCheckResult(1, "Be warned(!)")

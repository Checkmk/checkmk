#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.checkresults import ActiveCheckResult


class TestActiveCheckResult:
    @staticmethod
    def test_as_text_short():
        assert (
            ActiveCheckResult(
                state=1, summary="Make sure this has no trailing newlines and the like"
            ).as_text()
            == "Make sure this has no trailing newlines and the like"
        )

    @staticmethod
    def test_as_text_full():
        assert (
            ActiveCheckResult(
                state=2,
                summary="This is the summary",
                details=("Detail: 1", "Detail: 2"),
                metrics=("detail_count=2",),
            ).as_text()
            == "This is the summary | detail_count=2\nDetail: 1\nDetail: 2"
        )

    @staticmethod
    def test_as_text_sane():
        assert (
            ActiveCheckResult(
                state=2,
                summary="This | breaks things!",
                details=("Detail: | is special.",),
                metrics=("detail_count=2",),
            )
            .as_text()
            .count("|")
            == 1
        )

    @staticmethod
    def test_from_subresults() -> None:
        assert ActiveCheckResult.from_subresults(
            ActiveCheckResult(state=0, summary="Ok", details=("We're good",), metrics=("metric1",)),
            ActiveCheckResult(
                state=2, summary="Critical", details=("We're doomed",), metrics=("metric2",)
            ),
        ) == ActiveCheckResult(
            state=2,
            summary="Ok, Critical(!!)",
            details=("We're good", "We're doomed(!!)"),
            metrics=("metric1", "metric2"),
        )

    @staticmethod
    def test_active_check_result_no_redundant_state_markers() -> None:
        assert ActiveCheckResult.from_subresults(
            ActiveCheckResult.from_subresults(ActiveCheckResult(state=1, summary="Be warned")),
        ) == ActiveCheckResult(state=1, summary="Be warned(!)")

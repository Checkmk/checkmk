#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.graphing._valuespecs import MetricName

from .utils import expect_validate_failure, expect_validate_success


class TestValueSpecMetricName:
    def test_validate(self) -> None:
        expect_validate_failure(
            MetricName(),
            "_99",
            match=(
                "Metric names must only consist of letters, digits "
                "and underscores and they must start with a letter or digit."
            ),
        )
        expect_validate_failure(
            MetricName(),
            "",
            match=(
                "Metric names must only consist of letters, digits "
                "and underscores and they must start with a letter or digit."
            ),
        )
        expect_validate_failure(
            MetricName(),
            None,
        )
        expect_validate_success(MetricName(), "asd")
        expect_validate_success(MetricName(), "99asd")

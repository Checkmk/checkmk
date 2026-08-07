#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.legacy_checks.innovaphone_licenses import check_innovaphone_licenses


def test_check_innovaphone_licenses_metric_boundaries() -> None:
    _state, _message, perf = check_innovaphone_licenses(
        None, {"levels": (90.0, 95.0)}, [["100", "50"]]
    )
    assert perf == [("licenses", 50.0, None, None, 0, 100.0)]


@pytest.mark.xfail(strict=True, raises=ZeroDivisionError, reason="a total of 0 crashes the check")
def test_check_innovaphone_licenses_zero_total() -> None:
    assert check_innovaphone_licenses(None, {"levels": (90.0, 95.0)}, [["0", "0"]]) == (
        3,
        "Used 0/0 Licences",
        [("licenses", 0.0, None, None, 0, 0.0)],
    )

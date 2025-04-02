#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import freezegun
import pytest

from tests.testlib import set_timezone

import cmk.gui.valuespec as vs
from cmk.gui.exceptions import MKUserError

from .utils import (
    expect_validate_failure,
    expect_validate_success,
    raise_exception,
    request_var,
)


class TestAbsoluteDate:
    def test_validate(self) -> None:
        expect_validate_failure(vs.AbsoluteDate(), -1, match="not a valid Unix timestamp")
        expect_validate_failure(vs.AbsoluteDate(), 2**31, match="not a valid Unix timestamp")
        expect_validate_success(vs.AbsoluteDate(), 1662989393)
        expect_validate_failure(vs.AbsoluteDate(), None)
        expect_validate_success(vs.AbsoluteDate(allow_empty=True), None)
        expect_validate_failure(  # type: ignore[misc]
            vs.AbsoluteDate(),
            "smth",
            match="The type of the timestamp must be int or float, but is",
        )

    def test_json(self) -> None:
        assert vs.AbsoluteDate().value_from_json(11) == 11
        assert vs.AbsoluteDate().value_to_json(12) == 12

    def test_value_to_html(self) -> None:
        with set_timezone("UTC-2"):
            assert vs.AbsoluteDate().value_to_html(1631397600.0) == "2021-09-12"
            assert (
                vs.AbsoluteDate(include_time=True).value_to_html(1631453838.1)
                == "2021-09-12 15:37:18"
            )

    def test_mask(self) -> None:
        assert vs.AbsoluteDate().mask(1631397600.0) == 1631397600.0

    def test_from_html_vars(self) -> None:
        with set_timezone("UTC-2"):
            with request_var(a_year="2021", a_month="9", a_day="12"):
                assert vs.AbsoluteDate().from_html_vars("a") == 1631397600.0
            with request_var(
                a_year="2021",
                a_month="9",
                a_day="12",
                a_hour="15",
                a_min="37",
                a_sec="18",
            ):
                assert vs.AbsoluteDate(include_time=True).from_html_vars("a") == 1631453838.0
        with pytest.raises(MKUserError, match="Please enter a valid number"):
            with request_var(a_year="smth"):
                vs.AbsoluteDate().from_html_vars("a")
        with pytest.raises(MKUserError, match="The value for year must be between 1970 and 2038"):
            with request_var(a_year="2222"):
                vs.AbsoluteDate().from_html_vars("a")

        # TODO: it's allow_empty, not ignore_invalid_value, so we should expect an exception here
        with request_var(a_year="smth", a_month="smth", a_day="smth"):
            assert vs.AbsoluteDate(allow_empty=True).from_html_vars("a") is None
        # this one is fine:
        with request_var():
            assert vs.AbsoluteDate(allow_empty=True).from_html_vars("a") is None

    def test_default_value(self) -> None:
        assert vs.AbsoluteDate(default_value=123).default_value() == 123
        assert vs.AbsoluteDate(default_value=lambda: 234).default_value() == 234
        assert vs.AbsoluteDate(allow_empty=True).default_value() is None
        with freezegun.freeze_time("2022-09-12 16:07:49"):
            assert vs.AbsoluteDate().default_value() == 1662940800
            assert vs.AbsoluteDate(default_value=raise_exception).default_value() == 1662940800
            assert vs.AbsoluteDate(include_time=True).default_value() == 1662998869.0

    def test_canonical_value(self) -> None:
        assert vs.AbsoluteDate(default_value=123).canonical_value() == 123
        assert vs.AbsoluteDate(default_value=lambda: 234).canonical_value() == 234
        assert vs.AbsoluteDate(allow_empty=True).canonical_value() is None
        with freezegun.freeze_time("2022-09-12 16:07:49"):
            assert vs.AbsoluteDate().canonical_value() == 1662940800
            assert vs.AbsoluteDate(default_value=raise_exception).canonical_value() == 1662940800
            assert vs.AbsoluteDate(include_time=True).canonical_value() == 1662998869.0

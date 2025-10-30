#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import json
from collections.abc import Iterator

import pytest
from polyfactory.factories.typed_dict_factory import TypedDictFactory
from werkzeug.test import create_environ

from livestatus import OnlySites

from cmk.ccc.crash_reporting import CrashInfo
from cmk.gui.crash_reporting.pages import CrashReport, CrashReportRow
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Request


class CrashInfoFactory(TypedDictFactory[CrashInfo]):
    __model__ = CrashInfo


class FakeCrashReportsRowFetcher:
    def __init__(self, row: CrashReportRow | None = None) -> None:
        self._row = row

    def get_crash_report_rows(
        self, only_sites: OnlySites, filter_headers: str
    ) -> Iterator[dict[str, str]]:
        if self._row is not None:
            yield self._row


def test_build_crash_report() -> None:
    report = CrashReport.build(
        Request(create_environ(query_string="crash_id=1&site=heute")),
        FakeCrashReportsRowFetcher({"crash_info": json.dumps(CrashInfoFactory.build())}),
    )
    assert report.site_id == "heute"
    assert report.crash_id == "1"
    assert report.row["crash_info"] == json.dumps(report.info)


def test_build_crash_report_missing_row() -> None:
    with pytest.raises(MKUserError):
        CrashReport.build(
            Request(create_environ(query_string="crash_id=1&site=heute")),
            FakeCrashReportsRowFetcher(),
        )


def test_build_crash_report_missing_crash_report_key() -> None:
    with pytest.raises(KeyError):
        CrashReport.build(
            Request(create_environ(query_string="crash_id=1&site=heute")),
            FakeCrashReportsRowFetcher({"foo": "bar"}),
        )


@pytest.mark.parametrize(
    "query_string",
    [
        pytest.param("", id="no params"),
        pytest.param("crash_id=1", id="site missing"),
        pytest.param("site=heute", id="crash_id missing"),
    ],
)
def test_build_crash_report_missing_request_vars(query_string: str) -> None:
    with pytest.raises(MKUserError):
        CrashReport.build(
            Request(create_environ(query_string=query_string)),
            FakeCrashReportsRowFetcher({"crash_info": json.dumps(CrashInfoFactory.build())}),
        )

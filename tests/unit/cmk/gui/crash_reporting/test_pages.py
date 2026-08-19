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

from cmk.ccc.user import UserId
from cmk.crash import AggregatedCrashInfo
from cmk.gui.crash_reporting.pages import (
    _show_automatic_upload_hint,
    CrashReport,
    CrashReportRow,
    ReportRendererGUI,
    ReportRendererJavascript,
    show_automatic_upload_hint_on_view,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Request
from cmk.gui.utils.output_funnel import output_funnel


class CrashInfoFactory(TypedDictFactory[AggregatedCrashInfo]):
    __model__ = AggregatedCrashInfo


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


def _render_automatic_upload_hint(contact_email: str | None) -> str:
    with output_funnel.plugged():
        _show_automatic_upload_hint(Request(create_environ()), contact_email)
        return "".join(output_funnel.drain())


def test_automatic_upload_hint_shown_when_upload_disabled(with_admin_login: UserId) -> None:
    rendered = _render_automatic_upload_hint(None)

    assert "cmk-dialog" in rendered
    assert "mode=edit_configvar" in rendered
    assert "varname=automatic_crash_report_upload" in rendered


def test_automatic_upload_hint_hidden_when_upload_enabled(with_admin_login: UserId) -> None:
    assert _render_automatic_upload_hint("admin@example.com") == ""


def test_automatic_upload_hint_hidden_without_global_settings_permission(
    with_user_login: UserId,
) -> None:
    # The button leads to the global settings, which a non-admin user may not open.
    assert _render_automatic_upload_hint(None) == ""


@pytest.mark.parametrize(
    "view_name, expect_banner",
    [
        pytest.param("crash_reports", True, id="crash reports view"),
        pytest.param("hosts", False, id="unrelated view"),
    ],
)
def test_automatic_upload_hint_on_view(
    view_name: str, expect_banner: bool, with_admin_login: UserId
) -> None:
    with output_funnel.plugged():
        show_automatic_upload_hint_on_view(view_name)
        rendered = "".join(output_funnel.drain())

    assert ("cmk-dialog" in rendered) is expect_banner


def test_report_renderer_gui_show_details_without_request_details(request_context: None) -> None:
    # A GUI crash raised outside of a request (e.g. in a background job) is stored
    # with an empty details dict, so none of the request fields are available.
    crash_info = CrashInfoFactory.build(crash_type="gui", details={})

    with output_funnel.plugged():
        ReportRendererGUI().show_details(crash_info, {"crash_id": "1", "site": "heute"})
        rendered = "".join(output_funnel.drain())

    assert rendered == ""


def test_report_renderer_javascript_show_details(request_context: None) -> None:
    crash_info = CrashInfoFactory.build(
        crash_type="javascript",
        details={
            "url": "http://localhost/heute/check_mk/dashboard.py",
            "component": "DashboardApp",
            "user_agent": "Mozilla/5.0",
            "username": "cmkadmin",
            "language": "en",
            "context": "GET /heute/check_mk/api/internal/foo\nSTATUS 500",
        },
    )

    with output_funnel.plugged():
        ReportRendererJavascript().show_details(crash_info, {"crash_id": "1", "site": "heute"})
        rendered = "".join(output_funnel.drain())

    assert "http://localhost/heute/check_mk/dashboard.py" in rendered
    assert "DashboardApp" in rendered
    assert "Mozilla/5.0" in rendered
    assert "cmkadmin" in rendered
    assert "/heute/check_mk/api/internal/foo" in rendered


def test_report_renderer_javascript_show_details_without_details(request_context: None) -> None:
    crash_info = CrashInfoFactory.build(crash_type="javascript", details={})

    with output_funnel.plugged():
        ReportRendererJavascript().show_details(crash_info, {"crash_id": "1", "site": "heute"})
        rendered = "".join(output_funnel.drain())

    assert rendered == ""

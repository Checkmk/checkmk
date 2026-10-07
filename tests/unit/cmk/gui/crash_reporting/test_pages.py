#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import base64
import json
from collections.abc import Iterator, Mapping

import pytest
from polyfactory.factories.typed_dict_factory import TypedDictFactory
from werkzeug.test import create_environ

from livestatus import OnlySites

from cmk.ccc.site import SiteId
from cmk.crash import AggregatedCrashInfo
from cmk.gui.crash_reporting.pages import (
    _get_serialized_crash_report,
    _show_agent_output,
    _show_automatic_upload_hint,
    CrashReport,
    CrashReportRow,
    PageCrash,
    ReportRendererCheck,
    ReportRendererGeneric,
    ReportRendererGUI,
    ReportRendererJavascript,
    ReportRendererSection,
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
        self,
        only_sites: OnlySites,  # noqa: ARG002
        filter_headers: str,  # noqa: ARG002
    ) -> Iterator[CrashReportRow]:
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


@pytest.mark.usefixtures("with_admin_login")
def test_automatic_upload_hint_shown_when_upload_disabled() -> None:
    rendered = _render_automatic_upload_hint(None)

    assert "cmk-dialog" in rendered
    assert "global_settings.py" in rendered
    assert "varname=automatic_crash_report_upload" in rendered


@pytest.mark.usefixtures("with_admin_login")
def test_automatic_upload_hint_hidden_when_upload_enabled() -> None:
    assert _render_automatic_upload_hint("admin@example.com") == ""


@pytest.mark.usefixtures("with_user_login")
def test_automatic_upload_hint_hidden_without_global_settings_permission() -> None:
    # The button leads to the global settings, which a non-admin user may not open.
    assert _render_automatic_upload_hint(None) == ""


@pytest.mark.parametrize(
    "view_name, expect_banner",
    [
        pytest.param("crash_reports", True, id="crash reports view"),
        pytest.param("hosts", False, id="unrelated view"),
    ],
)
@pytest.mark.usefixtures("with_admin_login")
def test_automatic_upload_hint_on_view(view_name: str, expect_banner: bool) -> None:
    with output_funnel.plugged():
        show_automatic_upload_hint_on_view(view_name)
        rendered = "".join(output_funnel.drain())

    assert ("cmk-dialog" in rendered) is expect_banner


@pytest.mark.usefixtures("request_context")
def test_report_renderer_gui_show_details_without_request_details() -> None:
    # A GUI crash raised outside of a request (e.g. in a background job) is stored
    # with an empty details dict, so none of the request fields are available.
    crash_info = CrashInfoFactory.build(crash_type="gui", details={})

    with output_funnel.plugged():
        ReportRendererGUI().show_details(crash_info, {"crash_id": "1", "site": "heute"})
        rendered = "".join(output_funnel.drain())

    assert rendered == ""


@pytest.mark.usefixtures("request_context")
def test_report_renderer_javascript_show_details() -> None:
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


@pytest.mark.usefixtures("request_context")
def test_report_renderer_javascript_show_details_without_details() -> None:
    crash_info = CrashInfoFactory.build(crash_type="javascript", details={})

    with output_funnel.plugged():
        ReportRendererJavascript().show_details(crash_info, {"crash_id": "1", "site": "heute"})
        rendered = "".join(output_funnel.drain())

    assert rendered == ""


@pytest.mark.usefixtures("request_context")
def test_agent_output_with_undecodable_bytes_is_rendered() -> None:
    # Crash group 3818: a Windows agent sent output that is not valid UTF-8, so
    # the crash report page could not render it and replaced the page the user
    # opened to investigate the crash with a second crash.
    row: CrashReportRow = {"agent_output": "<<<check_mk>>>\nHostname: IS\udcff48186\n"}

    with output_funnel.plugged():
        _show_agent_output(row)
        rendered = "".join(output_funnel.drain())

    assert "check_mk" in rendered


def test_get_serialized_crash_report_with_bytes_crash_info() -> None:
    # Livestatus dynamic column reads crash.info file content as bytes.
    row: CrashReportRow = {
        "crash_info": b'{"core": "cmc"}',
        "crash_type": "gui",
        "crash_id": "f7541508-b5b6-11f1-bac8-145a415bde61",
        "site": "v300",
    }
    result = _get_serialized_crash_report(row)
    assert result["crash_info"] == b'{"core": "cmc"}'


LOCAL_FILE = "/omd/sites/heute/local/lib/python3/cmk_addons/plugins/acme/agent_based/acme.py"


def _minimal_crash_info(**fields: object) -> AggregatedCrashInfo:
    crash_info = CrashInfoFactory.build(
        **{
            "crash_type": "check",
            "exc_type": "ValueError",
            "exc_value": "boom",
            "local_vars": base64.b64encode(b"{}").decode(),
            "occurrences": {"first_seen": 1734000000.0, "last_seen": 1734000000.0, "count": 1},
            "details": {},
            **fields,
        }
    )
    if "exc_traceback" not in fields:
        crash_info.pop("exc_traceback", None)
    return crash_info


@pytest.mark.parametrize(
    "details, expect_warning",
    [
        pytest.param(
            {"vars": {"Password": "redacted", "host": "a"}}, True, id="sensitive request variable"
        ),
        pytest.param({"vars": {"host": "a"}}, False, id="harmless request variables"),
        pytest.param({}, False, id="no request variables"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_warn_about_sensitive_information(details: dict[str, object], expect_warning: bool) -> None:
    with output_funnel.plugged():
        PageCrash()._warn_about_sensitive_information(  # noqa: SLF001
            _minimal_crash_info(details=details)
        )
        rendered = "".join(output_funnel.drain())

    assert ("redact sensitive information" in rendered) is expect_warning


@pytest.mark.parametrize(
    "filepath, expect_warning",
    [
        pytest.param(LOCAL_FILE, True, id="local frame"),
        pytest.param("/omd/sites/heute/lib/python3/cmk/base/check_mk.py", False, id="no local"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_warn_about_local_files(filepath: str, expect_warning: bool) -> None:
    crash_info = _minimal_crash_info(
        exc_traceback=[(filepath, 1, "parse_acme", "return int(line)")]
    )

    with output_funnel.plugged():
        PageCrash()._warn_about_local_files(crash_info)  # noqa: SLF001
        rendered = "".join(output_funnel.drain())

    assert ("local hierarchy" in rendered) is expect_warning


@pytest.mark.usefixtures("request_context")
def test_warn_about_local_files_without_traceback() -> None:
    with output_funnel.plugged():
        PageCrash()._warn_about_local_files(_minimal_crash_info())  # noqa: SLF001
        rendered = "".join(output_funnel.drain())

    assert rendered == ""


@pytest.mark.usefixtures("request_context")
def test_show_crash_report_without_traceback() -> None:
    with output_funnel.plugged():
        PageCrash()._show_crash_report(_minimal_crash_info())  # noqa: SLF001
        rendered = "".join(output_funnel.drain())

    assert "ValueError (boom)" in rendered


CHECK_DETAILS = {
    "host": "myhost",
    "check_type": "acme_temp",
    "description": "Temperature Zone 1",
    "section": "MAIN_SECTION_CONTENT",
    "section_acme_temp": "NAMED_SECTION_CONTENT",
    "sectionless": "NOT_A_SECTION",
}


@pytest.mark.parametrize(
    "crash_type, renderer",
    [
        pytest.param("check", ReportRendererCheck, id="registered type"),
        pytest.param("no_such_crash_type", ReportRendererGeneric, id="unknown type"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_crash_type_renderer(crash_type: str, renderer: type) -> None:
    assert isinstance(PageCrash()._crash_type_renderer(crash_type), renderer)  # noqa: SLF001


def _render_check_details(details: Mapping[str, object]) -> str:
    with output_funnel.plugged():
        ReportRendererCheck().show_details(
            _minimal_crash_info(details=details), {"crash_id": "1", "site": "heute"}
        )
        return "".join(output_funnel.drain())


@pytest.mark.usefixtures("request_context")
def test_report_renderer_check_shows_section_keys() -> None:
    rendered = _render_check_details(CHECK_DETAILS)

    assert "MAIN_SECTION_CONTENT" in rendered
    assert "Section: acme_temp" in rendered
    assert "NAMED_SECTION_CONTENT" in rendered
    assert "NOT_A_SECTION" not in rendered


@pytest.mark.parametrize(
    "missing_key, row_title",
    [
        pytest.param("host", "Host", id="host"),
        pytest.param("check_type", "Check type", id="check type"),
        pytest.param("description", "Description", id="description"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_report_renderer_check_with_incomplete_details(missing_key: str, row_title: str) -> None:
    details = {k: v for k, v in CHECK_DETAILS.items() if k != missing_key}

    rendered = _render_check_details(details)

    assert all(str(value) in rendered for value in details.values() if value != "NOT_A_SECTION")
    assert f">{row_title}</td><td>Unknown</td>" in rendered


@pytest.mark.parametrize(
    "details, expected_titles",
    [
        pytest.param(CHECK_DETAILS, ["Host state", "Service state"], id="complete"),
        pytest.param({"host": "myhost"}, ["Host state"], id="without service"),
        pytest.param({}, [], id="without host"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_report_renderer_check_related_monitoring(
    details: dict[str, object], expected_titles: list[str]
) -> None:
    entries = ReportRendererCheck().page_menu_entries_related_monitoring(
        _minimal_crash_info(details=details), SiteId("heute")
    )

    assert [entry.title for entry in entries] == expected_titles


def _render_section_details(details: dict[str, object]) -> str:
    with output_funnel.plugged():
        ReportRendererSection().show_details(
            _minimal_crash_info(crash_type="section", details=details),
            {"crash_id": "1", "site": "heute"},
        )
        return "".join(output_funnel.drain())


@pytest.mark.parametrize(
    "inline_snmp, expected",
    [
        pytest.param(True, "Yes", id="inline snmp"),
        pytest.param(False, "No", id="classic snmp"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_report_renderer_section(inline_snmp: bool, expected: str) -> None:
    rendered = _render_section_details(
        {
            "section_name": "acme_temp",
            "inline_snmp": inline_snmp,
            "section_content": [["SECTION_LINE"]],
        }
    )

    assert "acme_temp" in rendered
    assert f"<pre>{expected}</pre>" in rendered
    assert "SECTION_LINE" in rendered


@pytest.mark.usefixtures("request_context")
def test_report_renderer_section_without_content() -> None:
    rendered = _render_section_details({"section_name": "acme_temp"})

    assert "<pre>Unknown</pre>" in rendered
    assert "String table" not in rendered


@pytest.mark.parametrize(
    "occurrences, expect_aggregate",
    [
        pytest.param(
            {"first_seen": 1734000000.0, "last_seen": 1734000000.0, "count": 1},
            False,
            id="single occurrence",
        ),
        pytest.param(
            {"first_seen": 1734000000.0, "last_seen": 1734090000.0, "count": 3},
            True,
            id="repeated occurrence",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_show_crash_report_occurrences(
    occurrences: dict[str, float], expect_aggregate: bool
) -> None:
    with output_funnel.plugged():
        PageCrash()._show_crash_report(  # noqa: SLF001
            _minimal_crash_info(occurrences=occurrences)
        )
        rendered = "".join(output_funnel.drain())

    assert ("(3 occurrences)" in rendered) is expect_aggregate
    assert ("First: " in rendered) is expect_aggregate

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.gui.htmllib.generator import ClickAction
from cmk.gui.monitor.export import EXPORT_EVENT, MonitorExportMenu, MonitorReportExportMenu
from cmk.gui.page_menu import PageMenuLink
from tests.testlib.unit.gui.global_settings import logged_in


@pytest.mark.usefixtures("user_without_permissions")
def test_export_dropdown_hidden_without_permission() -> None:
    assert MonitorExportMenu().dropdowns() == []


@pytest.mark.usefixtures("with_user_login")
def test_export_dropdown_offers_csv_and_json_with_permission() -> None:
    assert [
        entry.name
        for dropdown in MonitorExportMenu().dropdowns()
        for topic in dropdown.topics
        for entry in topic.entries
    ] == ["export_csv", "export_json"]


@pytest.mark.usefixtures("with_user_login")
def test_export_entries_dispatch_the_export_event_via_click_action() -> None:
    items = [
        entry.item
        for dropdown in MonitorExportMenu().dropdowns()
        for topic in dropdown.topics
        for entry in topic.entries
    ]

    assert [item.link.click_action for item in items if isinstance(item, PageMenuLink)] == [
        ClickAction(
            action="page_menu_dispatch_custom_event",
            arguments={"name": EXPORT_EVENT, "detail": export_format},
        )
        for export_format in ("csv", "json")
    ]


@pytest.mark.usefixtures("with_user_login")
def test_the_report_menu_offers_no_pdf_without_instant_reports() -> None:
    assert [
        entry.name
        for dropdown in MonitorReportExportMenu(instant_reports=False).dropdowns()
        for topic in dropdown.topics
        for entry in topic.entries
    ] == ["export_csv", "export_json"]


def _report_entries(user_id: UserId, *permissions: str) -> list[str | None]:
    with logged_in(user_id, "general.csv_export", *permissions):
        return [
            entry.name
            for dropdown in MonitorReportExportMenu(instant_reports=True).dropdowns()
            for topic in dropdown.topics
            for entry in topic.entries
        ]


def test_the_report_menu_offers_the_pdf_where_instant_reports_exist(
    with_user: tuple[UserId, str],
) -> None:
    assert _report_entries(with_user[0], "general.reporting", "general.instant_reports") == [
        "export_csv",
        "export_json",
        "export_pdf",
    ]


def test_the_report_menu_offers_no_pdf_to_a_user_without_instant_reports(
    with_user: tuple[UserId, str],
) -> None:
    assert _report_entries(with_user[0], "general.reporting") == ["export_csv", "export_json"]

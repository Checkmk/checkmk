#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final, Literal

from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_javascript_link, PageMenuDropdown, PageMenuEntry, PageMenuTopic
from cmk.web.utils.icons import IconNames, StaticIcon

EXPORT_EVENT: Final = "cmk-monitoring-export"

type ExportFormat = Literal["csv", "json"]


class MonitorExportMenu:
    def dropdowns(self) -> list[PageMenuDropdown]:
        if not (topics := self._topics()):
            return []
        return [PageMenuDropdown(name="export", title=_("Export"), topics=topics)]

    def _topics(self) -> list[PageMenuTopic]:
        if not user.may("general.csv_export"):
            return []
        return [
            PageMenuTopic(
                title=_("Data"),
                entries=[
                    self._entry(_("Export CSV"), StaticIcon(IconNames.download_csv), "csv"),
                    self._entry(_("Export JSON"), StaticIcon(IconNames.download_json), "json"),
                ],
            )
        ]

    @staticmethod
    def _entry(title: str, icon: StaticIcon, export_format: ExportFormat) -> PageMenuEntry:
        return PageMenuEntry(
            title=title,
            icon_name=icon,
            item=make_javascript_link(
                f"document.dispatchEvent(new CustomEvent('{EXPORT_EVENT}', "
                f"{{detail: '{export_format}'}}))"
            ),
            name=f"export_{export_format}",
        )

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pytest import MonkeyPatch

import cmk.utils.version as cmk_version
from cmk.utils.user import UserId

from cmk.gui.cee.plugins.reporting.utils import ReportSpec
from cmk.gui.sidebar._snapin.snapins import views


def test_report_menu_items(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.gui.cee.reporting.permitted_reports",
        lambda: {
            "test_report": ReportSpec(
                {
                    "elements": [],
                    "fixels": [],
                    "name": "test",
                    "use": "default",
                    "context": {},
                    "single_infos": [],
                    "title": "Title",
                    "owner": UserId("harry"),
                    "add_context_to_title": False,
                    "description": "descr",
                    "topic": "",
                    "sort_index": 99,
                    "is_show_more": False,
                    "packaged": False,
                    "hidebutton": False,
                    "hidden": False,
                    "icon": "",
                    "public": False,
                    "link_from": {},
                }
            ),
        },
    )
    if cmk_version.edition() is not cmk_version.Edition.CRE:
        expected = ["test_report"]
    else:
        expected = []

    assert [
        e[1][0] for e in views.view_menu_items(include_reports=True) if e[0] == "reports"
    ] == expected

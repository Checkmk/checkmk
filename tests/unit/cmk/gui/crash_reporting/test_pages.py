#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from polyfactory.factories.typed_dict_factory import TypedDictFactory

from cmk.ccc.crash_reporting import CrashInfo

from cmk.gui.crash_reporting.pages import ReportRendererGUI
from cmk.gui.utils.output_funnel import output_funnel


class CrashInfoFactory(TypedDictFactory[CrashInfo]):
    __model__ = CrashInfo


def test_report_renderer_gui_show_details_without_request_details(request_context: None) -> None:
    # A GUI crash raised outside of a request (e.g. in a background job) is stored
    # with an empty details dict, so none of the request fields are available.
    crash_info = CrashInfoFactory.build(crash_type="gui", details={})

    with output_funnel.plugged():
        ReportRendererGUI().show_details(crash_info, {"crash_id": "1", "site": "heute"})
        rendered = "".join(output_funnel.drain())

    assert rendered == ""

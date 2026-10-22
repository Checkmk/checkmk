#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.availability import AVLayoutTimeline
from cmk.gui.availability.view.rendering import render_timeline_bar
from cmk.gui.utils.output_funnel import output_funnel
from tests.unit.cmk.gui.compare_html import inline_event_handlers, ts_function_call


@pytest.mark.usefixtures("request_context")
def test_standalone_timeline_highlights_its_events_without_inline_handlers() -> None:
    layout: AVLayoutTimeline = {
        "range": (0.0, 3600.0),
        "spans": [(3, "OK", 100.0, "state0")],
        "time_choords": [],
        "render_date": str,
        "table": [],
    }

    with output_funnel.plugged():
        render_timeline_bar(layout, "standalone", timeline_nr=2)
        code = output_funnel.drain()

    assert inline_event_handlers(code) == []
    assert ts_function_call(code, "td#timeline_2_entry_3") == (
        "availability_timeline_hover",
        {"timeline_nr": 2, "row_nr": 3},
    )

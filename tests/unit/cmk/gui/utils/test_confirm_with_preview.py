#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.http import request
from cmk.gui.utils.confirm_with_preview import command_confirm_dialog
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel


@pytest.mark.usefixtures("request_context")
def test_command_confirm_dialog_cancel_leaves_action_mode() -> None:
    """Regression test for CMK-39728: cancel must show the full view with checkboxes again."""
    request.set_var("view_name", "crash_reports")
    request.set_var("show_checkboxes", "1")
    request.set_var("_do_actions", "yes")

    with output_funnel.plugged():
        command_confirm_dialog(
            confirm_options=[("Yes", "_do_yes")],
            command_title="Confirm",
            command_html=HTML.empty(),
            icon_class="question",
        )
        output = output_funnel.drain()

    marker = 'location.href = "'
    start = output.index(marker) + len(marker)
    cancel_url = output[start : output.index('"', start)]
    assert cancel_url == "index.py?show_checkboxes=1&view_name=crash_reports"

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.http import request
from cmk.gui.utils.confirm_with_preview import command_confirm_dialog, confirm_with_preview
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel


@pytest.mark.usefixtures("request_context")
def test_confirm_with_preview_form_action_preserves_view_context() -> None:
    """Regression test for CMK-34130: F5 on the "Back to view" page must not lose view_name.

    The confirm dialog's form action must include the current request's context vars (e.g.
    ``view_name``) so that the URL the browser lands on after submitting still identifies the
    view. Otherwise reloading the result page issues a GET to ``view.py`` without ``view_name``
    and the user sees "The requested view does not exist".
    """
    request.set_var("view_name", "services")
    request.set_var("host", "myhost")

    with output_funnel.plugged():
        confirm_with_preview("Are you sure?", [("Yes", "_do_yes")])
        output = output_funnel.drain()

    form_action = _extract_form_action(output)
    assert "view_name=services" in form_action
    assert "host=myhost" in form_action


@pytest.mark.usefixtures("request_context")
def test_command_confirm_dialog_form_action_preserves_view_context() -> None:
    """Regression test for CMK-34130 (command confirm dialog variant)."""
    request.set_var("view_name", "services")
    request.set_var("host", "myhost")

    with output_funnel.plugged():
        command_confirm_dialog(
            confirm_options=[("Yes", "_do_yes")],
            command_title="Confirm",
            command_html=HTML.empty(),
            icon_class="question",
        )
        output = output_funnel.drain()

    form_action = _extract_form_action(output)
    assert "view_name=services" in form_action
    assert "host=myhost" in form_action


def _extract_form_action(output: str) -> str:
    marker = 'action="'
    start = output.index(marker) + len(marker)
    end = output.index('"', start)
    return output[start:end]

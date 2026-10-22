#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.valuespec as vs
from cmk.gui.htmllib.generator import TSFunctionCall
from tests.unit.cmk.gui.compare_html import inline_event_handlers, ts_function_call

from .utils import render_input


@pytest.mark.parametrize(
    "picker",
    [
        pytest.param(vs.DatePicker(), id="date"),
        pytest.param(vs.TimePicker(), id="time"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_picker_renders_without_inline_event_handlers(picker: vs.ValueSpec[str]) -> None:
    assert inline_event_handlers(render_input(picker, "")) == []


@pytest.mark.usefixtures("request_context")
def test_date_picker_calls_its_change_function() -> None:
    picker = vs.DatePicker(on_change=TSFunctionCall(function_name="set_focus_by_id"))

    assert ts_function_call(render_input(picker, ""), "cmk-date-time-picker") == (
        "set_focus_by_id",
        {},
    )

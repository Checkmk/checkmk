#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.logged_in import LoggedInUser, UserDefaultConfig
from cmk.gui.painter import Cell
from cmk.gui.painter.painters import (
    make_svc_long_plugin_output_painter,
    make_svc_next_check_painter,
    MAX_LONG_OUTPUT_SIZE,
)
from cmk.gui.type_defs import ColumnSpec, Row
from cmk.gui.utils.roles import UserPermissions
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context

_PERMISSIONS = UserPermissions({}, {}, {}, [])
_USER = LoggedInUser(
    None,
    _PERMISSIONS,
    defaults=UserDefaultConfig(users={}, default_language="en", default_show_mode="default"),
)


def test_long_output_painter_warns_about_output_cut_at_the_site_limit() -> None:
    row: Row = {
        "site": "NO_SITE",
        "service_long_plugin_output": "x" * 3000,
        MAX_LONG_OUTPUT_SIZE: 2000,
    }
    painter = make_svc_long_plugin_output_painter()
    context = make_painter_context(_PERMISSIONS)
    ident = "svc_long_plugin_output"
    cell = Cell(ColumnSpec(name=ident), None, {ident: painter}, context, None)
    _css, content = painter.render(row, cell, _USER, context)
    assert "Lost data due to truncation of long output to 2kB" in str(content)


def _render_next_check(row: Row) -> str:
    painter = make_svc_next_check_painter()
    context = make_painter_context(_PERMISSIONS)
    ident = "svc_next_check"
    cell = Cell(ColumnSpec(name=ident), None, {ident: painter}, context, None)
    _css, content = painter.render(row, cell, _USER, context)
    return str(content)


def test_next_check_of_an_active_check_the_relay_runs_is_managed_by_the_relay() -> None:
    row: Row = {
        "service_next_check": 0,
        "service_check_type": 0,
        "host_labels": {"cmk/relay": "relay_a"},
    }

    assert _render_next_check(row) == "Managed by the relay"


@pytest.mark.parametrize(
    "row",
    [
        pytest.param(
            {
                "service_next_check": 0,
                "service_check_type": 1,
                "host_labels": {"cmk/relay": "relay_a"},
            },
            id="passive service of a relay host",
        ),
        pytest.param(
            {"service_next_check": 0, "service_check_type": 0, "host_labels": {}},
            id="active check of a site host",
        ),
    ],
)
def test_unscheduled_next_check_not_run_by_a_relay_is_a_dash(row: Row) -> None:
    assert _render_next_check(row) == "-"

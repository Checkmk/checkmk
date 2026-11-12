#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.painter.v0 import Cell
from cmk.gui.painter.v0.helpers import RenderLink
from cmk.gui.painter.v0.painters import PainterSvcNextCheck
from cmk.gui.painter_options import PainterOptions
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import Row
from cmk.gui.utils.roles import UserPermissions


def _render_next_check(row: Row) -> str:
    permissions = UserPermissions({}, {}, {}, [])
    painter = PainterSvcNextCheck(
        config=active_config,
        request=request,
        painter_options=PainterOptions.get_instance(),
        theme=theme,
        url_renderer=RenderLink(request, response, display_options),
        user_permissions=permissions,
    )
    _css, content = painter.render(row, Cell(None, None, None, permissions), user)
    return str(content)


@pytest.mark.usefixtures("request_context")
def test_next_check_of_an_active_check_the_relay_runs_is_managed_by_the_relay() -> None:
    row: Row = {
        "service_next_check": 0,
        "service_check_type": 0,
        "host_labels": {"cmk/relay": "relay_a"},
    }

    assert _render_next_check(row) == "Managed by the relay"


@pytest.mark.usefixtures("request_context")
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

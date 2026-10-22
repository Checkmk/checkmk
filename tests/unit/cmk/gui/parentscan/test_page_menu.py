#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.parentscan.page_menu import render_host_action_menu_entry
from cmk.gui.utils.output_funnel import output_funnel
from tests.unit.cmk.gui.compare_html import click_handling


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_host_action_menu_entry_scans_for_parents_by_click_action() -> None:
    with output_funnel.plugged():
        render_host_action_menu_entry(HostName("heute"), "hosts")
        code = output_funnel.drain()

    assert click_handling(code, "a") == (
        None,
        "form_submit_for_single_host",
        {"form_name": "hosts", "button_name": "_parentscan"},
    )

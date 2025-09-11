#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.gui.type_defs import Visual
from cmk.gui.views.inventory import find_non_canonical_filters
from cmk.gui.views.inventory.registry import inventory_displayhints
from cmk.gui.visuals import TVisual
from cmk.update_config.plugins.actions.visuals import _migrate_visual


@pytest.mark.parametrize(
    "visual, result",
    [
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "foo": {
                        "bar_from": "123",
                        "bar_until": "456",
                    },
                },
                single_infos=[],
                add_context_to_title=False,
                title="",
                description="",
                topic="",
                sort_index=1,
                is_show_more=False,
                icon="",
                hidden=False,
                hidebutton=False,
                public=False,
                packaged=False,
                link_from={},
                main_menu_search_terms=[],
            ),
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "foo": {
                        "bar_from": "123",
                        "bar_until": "456",
                    },
                },
                single_infos=[],
                add_context_to_title=False,
                title="",
                description="",
                topic="",
                sort_index=1,
                is_show_more=False,
                icon="",
                hidden=False,
                hidebutton=False,
                public=False,
                packaged=False,
                link_from={},
                main_menu_search_terms=[],
            ),
            id="canonical-inv-filters",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "inv_hardware_cpu_bus_speed": {
                        "inv_hardware_cpu_bus_speed_from": "1",
                        "inv_hardware_cpu_bus_speed_until": "2",
                    },
                    "inv_hardware_memory_total_ram_usable": {
                        "inv_hardware_memory_total_ram_usable_from": "3",
                        "inv_hardware_memory_total_ram_usable_until": "4",
                    },
                    "inv_hardware_cpu_cache_size": {
                        "inv_hardware_cpu_cache_size_from": "5",
                        "inv_hardware_cpu_cache_size_until": "6",
                    },
                },
                single_infos=[],
                add_context_to_title=False,
                title="",
                description="",
                topic="",
                sort_index=1,
                is_show_more=False,
                icon="",
                hidden=False,
                hidebutton=False,
                public=False,
                packaged=False,
                link_from={},
                main_menu_search_terms=[],
            ),
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "inv_hardware_cpu_bus_speed": {
                        "inv_hardware_cpu_bus_speed_canonical_from": "1000000",
                        "inv_hardware_cpu_bus_speed_canonical_until": "2000000",
                    },
                    "inv_hardware_memory_total_ram_usable": {
                        "inv_hardware_memory_total_ram_usable_canonical_from": "3145728",
                        "inv_hardware_memory_total_ram_usable_canonical_until": "4194304",
                    },
                    "inv_hardware_cpu_cache_size": {
                        "inv_hardware_cpu_cache_size_canonical_from": "5242880",
                        "inv_hardware_cpu_cache_size_canonical_until": "6291456",
                    },
                },
                single_infos=[],
                add_context_to_title=False,
                title="",
                description="",
                topic="",
                sort_index=1,
                is_show_more=False,
                icon="",
                hidden=False,
                hidebutton=False,
                public=False,
                packaged=False,
                link_from={},
                main_menu_search_terms=[],
            ),
            id="non-canonical-inv-filters",
        ),
    ],
)
def test__migrate_visual(visual: TVisual, result: TVisual) -> None:
    assert _migrate_visual(visual, find_non_canonical_filters(inventory_displayhints)) == result
    assert _migrate_visual(result, find_non_canonical_filters(inventory_displayhints)) == result

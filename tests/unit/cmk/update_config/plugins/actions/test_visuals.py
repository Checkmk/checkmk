#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.ccc.user import UserId
from cmk.discover_plugins import DiscoveredPlugins, PluginLocation
from cmk.gui.type_defs import Visual
from cmk.gui.views.inventory import (
    find_non_canonical_filters,
    InventoryHintSpec,
)
from cmk.gui.visuals import TVisual
from cmk.inventory_ui.v1_unstable import AgeNotation as AgeNotationFromAPI
from cmk.inventory_ui.v1_unstable import Node as NodeFromAPI
from cmk.inventory_ui.v1_unstable import NumberField as NumberFieldFromAPI
from cmk.inventory_ui.v1_unstable import Table as TableFromAPI
from cmk.inventory_ui.v1_unstable import Title as TitleFromAPI
from cmk.inventory_ui.v1_unstable import Unit as UnitFromAPI
from cmk.inventory_ui.v1_unstable import View as ViewFromAPI
from cmk.update_config.plugins.actions.visuals import migrate_visuals

_PLUGINS = DiscoveredPlugins(
    [],
    {
        PluginLocation("module", "node_interface"): NodeFromAPI(
            name="interface",
            path=["interface"],
            title=TitleFromAPI("Node title"),
            table=TableFromAPI(
                view=ViewFromAPI(
                    name="invinterface",
                    title=TitleFromAPI("Node title view"),
                ),
                columns={
                    "last_change": NumberFieldFromAPI(
                        TitleFromAPI("Column title"),
                        render=UnitFromAPI(AgeNotationFromAPI()),
                    ),
                },
            ),
        ),
    },
)
_LEGACY_HINTS: Mapping[str, InventoryHintSpec] = {
    ".hardware.cpu.max_speed": {"title": "Maximum speed", "paint": "hz"},
    ".hardware.memory.total_ram_usable": {"title": "Total usable RAM", "paint": "bytes_rounded"},
    ".hardware.cpu.cache_size": {"title": "Cache size", "paint": "bytes"},
}


@pytest.mark.parametrize(
    "visual, expected_has_changed, expected_visual",
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
            False,
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
            id="canonical-inv-attrs-filters",
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
            True,
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "inv_hardware_cpu_bus_speed_canonical": {
                        "inv_hardware_cpu_bus_speed_canonical_from": "1000000",
                        "inv_hardware_cpu_bus_speed_canonical_until": "2000000",
                    },
                    "inv_hardware_memory_total_ram_usable_canonical": {
                        "inv_hardware_memory_total_ram_usable_canonical_from": "3145728",
                        "inv_hardware_memory_total_ram_usable_canonical_until": "4194304",
                    },
                    "inv_hardware_cpu_cache_size_canonical": {
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
            id="non-canonical-inv-attrs-filters",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_last_change": {
                        "invinterface_last_change_from_days": "1",
                        "invinterface_last_change_until_days": "2",
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
            True,
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_last_change_canonical": {
                        "invinterface_last_change_canonical_from": "86400",
                        "invinterface_last_change_canonical_until": "172800",
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
            id="non-canonical-inv-table-filters",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_last_change": {
                        "invinterface_last_change_from_days": "1",
                        "invinterface_last_change_until_days": "2",
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
            True,
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_last_change_canonical": {
                        "invinterface_last_change_canonical_from": "86400",
                        "invinterface_last_change_canonical_until": "172800",
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
            id="non-canonical-inv-table-filters",
        ),
    ],
)
def test__migrate_visual(
    visual: TVisual, expected_has_changed: bool, expected_visual: TVisual
) -> None:
    non_canonical_filters = find_non_canonical_filters(_PLUGINS, _LEGACY_HINTS)

    migration = migrate_visuals({(UserId("userid"), "name"): visual}, non_canonical_filters)
    assert migration.has_changed is expected_has_changed
    assert migration.migrated == {"userid": {("userid", "name"): expected_visual}}

    migration = migrate_visuals(
        {(UserId("userid"), "name"): expected_visual}, non_canonical_filters
    )
    assert not migration.has_changed
    assert migration.migrated == {"userid": {("userid", "name"): expected_visual}}

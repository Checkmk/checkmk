#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.ccc.user import UserId
from cmk.discover_plugins import DiscoveredPlugins, PluginLocation
from cmk.gui.inventory.filters import (
    FilterInvtableAdminStatus,
    FilterInvtableAvailable,
    FilterInvtableInterfaceType,
    FilterInvtableOperStatus,
    FilterInvtableTimestampAsAge,
)
from cmk.gui.type_defs import Visual
from cmk.gui.views.inventory import (
    find_non_canonical_filters,
    InventoryHintSpec,
)
from cmk.gui.visuals import TVisual
from cmk.inventory_ui.v1_unstable import AgeNotation as AgeNotationFromAPI
from cmk.inventory_ui.v1_unstable import BoolField as BoolFieldFromAPI
from cmk.inventory_ui.v1_unstable import ChoiceField as ChoiceFieldFromAPI
from cmk.inventory_ui.v1_unstable import IECNotation as IECNotationFromAPI
from cmk.inventory_ui.v1_unstable import Label as LabelFromAPI
from cmk.inventory_ui.v1_unstable import Node as NodeFromAPI
from cmk.inventory_ui.v1_unstable import NumberField as NumberFieldFromAPI
from cmk.inventory_ui.v1_unstable import SINotation as SINotationFromAPI
from cmk.inventory_ui.v1_unstable import Table as TableFromAPI
from cmk.inventory_ui.v1_unstable import Title as TitleFromAPI
from cmk.inventory_ui.v1_unstable import Unit as UnitFromAPI
from cmk.inventory_ui.v1_unstable import View as ViewFromAPI
from cmk.update_config.plugins.actions.visuals import migrate_visuals

_PLUGINS = DiscoveredPlugins(
    [],
    {
        PluginLocation("module", "node_hardware_cpu"): NodeFromAPI(
            name="hardware_cpu",
            path=["hardware", "cpu"],
            title=TitleFromAPI("Processor"),
            attributes={
                "cache_size": NumberFieldFromAPI(
                    TitleFromAPI("Cache size"), render=UnitFromAPI(IECNotationFromAPI("B"))
                ),
                "bus_speed": NumberFieldFromAPI(
                    TitleFromAPI("Bus speed"), render=UnitFromAPI(SINotationFromAPI("Hz"))
                ),
            },
        ),
        PluginLocation("module", "node_hardware_memory"): NodeFromAPI(
            name="hardware_memory",
            path=["hardware", "memory"],
            title=TitleFromAPI("Memory (RAM)"),
            attributes={
                "total_ram_usable": NumberFieldFromAPI(
                    TitleFromAPI("Total usable RAM"), render=UnitFromAPI(IECNotationFromAPI("B"))
                ),
                "foobar": BoolFieldFromAPI(
                    TitleFromAPI("Foo bar"),
                    render_true=LabelFromAPI("It's true"),
                    render_false=LabelFromAPI("It's false"),
                ),
            },
        ),
        PluginLocation("module", "node_networking_interfaces"): NodeFromAPI(
            name="networking_interfaces",
            path=["networking", "interfaces"],
            title=TitleFromAPI("Networking interfaces"),
            table=TableFromAPI(
                view=ViewFromAPI(
                    name="invinterface",
                    title=TitleFromAPI("Node title view"),
                ),
                columns={
                    "last_change": NumberFieldFromAPI(
                        TitleFromAPI("Last change"),
                        render=UnitFromAPI(AgeNotationFromAPI()),
                    ),
                    "oper_status": ChoiceFieldFromAPI(
                        TitleFromAPI("Operational status"),
                        mapping={
                            1: "1 - up",
                            2: "2 - down",
                            3: "3 - testing",
                            4: "4 - unknown",
                            5: "5 - dormant",
                            6: "6 - not present",
                            7: "7 - lower layer down",
                        },
                    ),
                    "admin_status": ChoiceFieldFromAPI(
                        TitleFromAPI("Administrative status"),
                        mapping={
                            1: "1 - up",
                            2: "2 - down",
                        },
                    ),
                    "port_type": ChoiceFieldFromAPI(
                        TitleFromAPI("Type"),
                        mapping={
                            1: "1 - other",
                            2: "2 - regular1822",
                            3: "3 - hdh1822",
                            4: "4 - ddnX25",
                            5: "5 - rfc877x25",
                            6: "6 - ethernetCsmacd",
                            7: "7 - iso88023Csmacd",
                            8: "8 - iso88024TokenBus",
                            9: "9 - iso88025TokenRing",
                            10: "10 - iso88026Man",
                            11: "11 - starLan",
                            12: "12 - proteon10Mbit",
                            13: "13 - proteon80Mbit",
                            14: "14 - hyperchannel",
                            15: "15 - fddi",
                        },
                    ),
                    "available": BoolFieldFromAPI(
                        TitleFromAPI("Port usage"),
                        render_true=LabelFromAPI("Free"),
                        render_false=LabelFromAPI("Used"),
                    ),
                },
            ),
        ),
    },
)
_LEGACY_HINTS: Mapping[str, InventoryHintSpec] = {
    ".hardware.cpu.max_speed": {"title": "Maximum speed", "paint": "hz"},
    ".hardware.cpu.cache_size": {"title": "Cache size", "paint": "bytes"},
    ".networking.interfaces:": {
        "title": "Network interfaces",
        "keyorder": [
            "oper_status",
            "admin_status",
            "available",
            "last_change",
            "port_type",
        ],
        "view": "invinterface",
        "is_show_more": False,
    },
    ".hardware.memory.total_ram_usable": {"title": "Total usable RAM", "paint": "bytes_rounded"},
    ".hardware.memory.foobar": {"title": "Foo bar", "paint": "bool"},
    ".networking.interfaces:*.oper_status": {
        "title": "Operational status",
        "paint": "if_oper_status",
        "filter": FilterInvtableOperStatus,
    },
    ".networking.interfaces:*.admin_status": {
        "title": "Administrative status",
        "paint": "if_admin_status",
        "filter": FilterInvtableAdminStatus,
    },
    ".networking.interfaces:*.available": {
        "title": "Port usage",
        "paint": "if_available",
        "filter": FilterInvtableAvailable,
    },
    ".networking.interfaces:*.last_change": {
        "title": "Last change",
        "paint": "timestamp_as_age_days",
        "filter": FilterInvtableTimestampAsAge,
    },
    ".networking.interfaces:*.port_type": {
        "title": "Type",
        "paint": "if_port_type",
        "filter": FilterInvtableInterfaceType,
    },
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
                    "inv_hardware_memory_foobar": {
                        "is_inv_hardware_memory_foobar": "1",
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
                    "inv_hardware_memory_foobar": {
                        "inv_hardware_memory_foobar_True": "on",
                        "inv_hardware_memory_foobar_False": "",
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
            id="inv-attrs-filter-bool-true",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "inv_hardware_memory_foobar": {
                        "is_inv_hardware_memory_foobar": "0",
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
                    "inv_hardware_memory_foobar": {
                        "inv_hardware_memory_foobar_True": "",
                        "inv_hardware_memory_foobar_False": "on",
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
            id="inv-attrs-filter-bool-false",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "inv_hardware_memory_foobar": {
                        "is_inv_hardware_memory_foobar": "-1",
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
                    "inv_hardware_memory_foobar": {
                        "inv_hardware_memory_foobar_False": "on",
                        "inv_hardware_memory_foobar_True": "on",
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
            id="inv-attrs-filter-bool-ignore",
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
            id="non-canonical-inv-table-filter-last-change",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_oper_status": {
                        "invinterface_oper_status_1": "",
                        "invinterface_oper_status_2": "on",
                        "invinterface_oper_status_3": "",
                        "invinterface_oper_status_4": "",
                        "invinterface_oper_status_5": "",
                        "invinterface_oper_status_6": "on",
                        "invinterface_oper_status_7": "",
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
                    "invinterface_oper_status": {
                        "invinterface_oper_status_1": "",
                        "invinterface_oper_status_2": "on",
                        "invinterface_oper_status_3": "",
                        "invinterface_oper_status_4": "",
                        "invinterface_oper_status_5": "",
                        "invinterface_oper_status_6": "on",
                        "invinterface_oper_status_7": "",
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
            id="non-canonical-inv-table-filter-oper-status",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_admin_status": {
                        "invinterface_admin_status": "-1",
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
                    "invinterface_admin_status": {
                        "invinterface_admin_status_1": "on",
                        "invinterface_admin_status_2": "on",
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
            id="non-canonical-inv-table-filter-admin-status-ignore",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_admin_status": {
                        "invinterface_admin_status": "1",
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
                    "invinterface_admin_status": {
                        "invinterface_admin_status_1": "on",
                        "invinterface_admin_status_2": "",
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
            id="non-canonical-inv-table-filter-admin-status-up",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_admin_status": {
                        "invinterface_admin_status": "2",
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
                    "invinterface_admin_status": {
                        "invinterface_admin_status_1": "",
                        "invinterface_admin_status_2": "on",
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
            id="non-canonical-inv-table-filter-admin-status-down",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_port_type": {
                        "invinterface_port_type": "1|2|3",
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
                    "invinterface_port_type": {
                        "invinterface_port_type": "1|2|3",
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
            id="non-canonical-inv-table-filter-port-type",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_available": {
                        "invinterface_available": "",
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
                    "invinterface_available": {
                        "invinterface_available_False": "on",
                        "invinterface_available_True": "on",
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
            id="non-canonical-inv-table-filter-available-ignore",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_available": {
                        "invinterface_available": "yes",
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
                    "invinterface_available": {
                        "invinterface_available_True": "on",
                        "invinterface_available_False": "",
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
            id="non-canonical-inv-table-filter-available-free",
        ),
        pytest.param(
            Visual(
                owner=UserId("user"),
                name="",
                context={
                    "invinterface_available": {
                        "invinterface_available": "no",
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
                    "invinterface_available": {
                        "invinterface_available_True": "",
                        "invinterface_available_False": "on",
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
            id="non-canonical-inv-table-filter-available-used",
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

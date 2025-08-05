#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
from collections.abc import Callable

# No stub file
import pytest

import cmk.gui.inventory
import cmk.gui.utils
from cmk.gui.inventory._tree import InventoryPath, TreeSource
from cmk.gui.inventory.filters import (
    FilterInvtableText,
    FilterInvText,
)
from cmk.gui.num_split import cmp_version
from cmk.gui.utils.html import HTML
from cmk.gui.views.inventory._display_hints import (
    _cmp_inv_generic,
    _decorate_sort_function,
    _get_related_legacy_hints,
    _PaintBool,
    _PaintChoice,
    _PaintNumber,
    _PaintText,
    _parse_view_name,
    _RelatedLegacyHints,
    _SortFunctionChoice,
    _SortFunctionText,
    AttributeDisplayHint,
    ColumnDisplayHint,
    ColumnDisplayHintOfView,
    inv_display_hints,
    NodeDisplayHint,
    Table,
    TableWithView,
)
from cmk.gui.views.inventory._paint_functions import (
    inv_paint_generic,
    inv_paint_if_oper_status,
    inv_paint_number,
    inv_paint_service_status,
    inv_paint_size,
)
from cmk.gui.views.inventory.registry import inventory_displayhints
from cmk.inventory_ui.v1_alpha import AgeNotation as AgeNotationFromAPI
from cmk.inventory_ui.v1_alpha import Alignment as AlignmentFromAPI
from cmk.inventory_ui.v1_alpha import BoolField as BoolFieldFromAPI
from cmk.inventory_ui.v1_alpha import ChoiceField as ChoiceFieldFromAPI
from cmk.inventory_ui.v1_alpha import DecimalNotation as DecimalNotationFromAPI
from cmk.inventory_ui.v1_alpha import IECNotation as IECNotationFromAPI
from cmk.inventory_ui.v1_alpha import Label as LabelFromAPI
from cmk.inventory_ui.v1_alpha import LabelColor as LabelColorFromAPI
from cmk.inventory_ui.v1_alpha import NumberField as NumberFieldFromAPI
from cmk.inventory_ui.v1_alpha import SINotation as SINotationFromAPI
from cmk.inventory_ui.v1_alpha import (
    StandardScientificNotation as StandardScientificNotationFromAPI,
)
from cmk.inventory_ui.v1_alpha import TextField as TextFieldFromAPI
from cmk.inventory_ui.v1_alpha import TimeNotation as TimeNotationFromAPI
from cmk.inventory_ui.v1_alpha import Title as TitleFromAPI
from cmk.inventory_ui.v1_alpha import Unit as UnitFromAPI
from cmk.utils.structured_data import SDKey, SDNodeName, SDPath


def test_display_hint_titles() -> None:
    assert all("title" in hint for hint in inventory_displayhints.values())


_IGNORED_KEYS_BY_PATH = {
    ("hardware", "system"): ["serial_number", "model_name"],
    ("hardware", "storage", "disks"): [
        "drive_index",
        "bus",
        "serial",
        "local",
        "size",
        "product",
        "type",
        "vendor",
    ],
    ("software", "applications", "vmwareesx"): ["clusters"],
}


def test_related_display_hints() -> None:
    # Each node of a display hint (especially for table columns or attributes) must have a display
    # hint, too.
    # Example:
    #   If you add the attribute hint
    #       ".software.applications.fritz.link_type"
    #   then the following hints must exist:
    #       ".software.applications.fritz.",
    #       ".software.applications.",
    #       ".software.",

    # XOR: We have either
    #   - real nodes, eg. ".hardware.chassis.",
    #   - nodes with attributes, eg. ".hardware.cpu." or
    #   - nodes with a table, eg. ".software.packages:"

    all_related_legacy_hints = _get_related_legacy_hints(inventory_displayhints)

    def _check_path(path: SDPath) -> bool:
        return all(path[:idx] in all_related_legacy_hints for idx in range(1, len(path)))

    def _check_legacy_hints(related_legacy_hints: _RelatedLegacyHints) -> bool:
        return bool(related_legacy_hints.for_node) ^ bool(related_legacy_hints.for_table)

    def _check_table_key_order(path: SDPath, related_legacy_hints: _RelatedLegacyHints) -> bool:
        ignored_keys = set(_IGNORED_KEYS_BY_PATH.get(path, []))
        return (
            set(related_legacy_hints.for_table.get("keyorder", [])) - ignored_keys
            == set(related_legacy_hints.by_column) - ignored_keys
        )

    def _check_attributes_key_order(
        path: SDPath, related_legacy_hints: _RelatedLegacyHints
    ) -> bool:
        ignored_keys = set(_IGNORED_KEYS_BY_PATH.get(path, []))
        return (
            set(related_legacy_hints.for_node.get("keyorder", [])) - ignored_keys
            == set(related_legacy_hints.by_key) - ignored_keys
        )

    for path, related_legacy_hints in _get_related_legacy_hints(inventory_displayhints).items():
        assert _check_path(path)
        assert _check_legacy_hints(related_legacy_hints)
        assert _check_table_key_order(path, related_legacy_hints)
        assert _check_attributes_key_order(path, related_legacy_hints)


def test_missing_table_keyorder() -> None:
    ignore_paths = [
        ".hardware.memory.arrays:",  # Has no table
        ".software.applications.vmwareesx:",
    ]

    missing_keyorders = [
        path
        for path, hint in inventory_displayhints.items()
        if path.endswith(":") and path not in ignore_paths and not hint.get("keyorder")
    ]

    # TODO test second part
    assert missing_keyorders == [], (
        "Missing 'keyorder' in %s. The 'keyorder' should contain at least the key columns."
        % ",".join(missing_keyorders)
    )


@pytest.mark.parametrize(
    "val_a, val_b, result",
    [
        (None, None, 0),
        (None, 0, -1),
        (0, None, 1),
        (0, 0, 0),
        (1, 0, 1),
        (0, 1, -1),
    ],
)
def test__cmp_inv_generic(val_a: object, val_b: object, result: int) -> None:
    assert _decorate_sort_function(_cmp_inv_generic)(val_a, val_b) == result


@pytest.mark.parametrize(
    "path, expected_node_hint",
    [
        (
            (),
            NodeDisplayHint(
                name="inv",
                path=(),
                icon="",
                title="Inventory tree",
                short_title="Inventory tree",
                long_title="Inventory tree",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ("hardware",),
            NodeDisplayHint(
                path=(SDNodeName("hardware"),),
                name="inv_hardware",
                icon="hardware",
                title="Hardware",
                short_title="Hardware",
                long_title="Hardware",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ("hardware", "cpu"),
            NodeDisplayHint(
                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                name="inv_hardware_cpu",
                icon="",
                title="Processor",
                short_title="Processor",
                long_title="Hardware ➤ Processor",
                # The single attribute hints are not checked here
                attributes={
                    SDKey("arch"): AttributeDisplayHint(
                        name="inv_hardware_cpu_arch",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_arch",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("arch"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("max_speed"): AttributeDisplayHint(
                        name="inv_hardware_cpu_max_speed",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_max_speed",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("max_speed"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("model"): AttributeDisplayHint(
                        name="inv_hardware_cpu_model",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_model",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("model"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("type"): AttributeDisplayHint(
                        name="inv_hardware_cpu_type",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_type",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("type"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("threads"): AttributeDisplayHint(
                        name="inv_hardware_cpu_threads",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_threads",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("threads"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("smt_threads"): AttributeDisplayHint(
                        name="inv_hardware_cpu_smt_threads",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_smt_threads",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("smt_threads"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("cpu_max_capa"): AttributeDisplayHint(
                        name="inv_hardware_cpu_cpu_max_capa",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_cpu_max_capa",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("cpu_max_capa"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("cpus"): AttributeDisplayHint(
                        name="inv_hardware_cpu_cpus",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_cpus",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("cpus"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("logical_cpus"): AttributeDisplayHint(
                        name="inv_hardware_cpu_logical_cpus",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_logical_cpus",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("logical_cpus"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("cores"): AttributeDisplayHint(
                        name="inv_hardware_cpu_cores",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_cores",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("cores"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("cores_per_cpu"): AttributeDisplayHint(
                        name="inv_hardware_cpu_cores_per_cpu",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_cores_per_cpu",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("cores_per_cpu"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("threads_per_cpu"): AttributeDisplayHint(
                        name="inv_hardware_cpu_threads_per_cpu",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_threads_per_cpu",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("threads_per_cpu"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("cache_size"): AttributeDisplayHint(
                        name="inv_hardware_cpu_cache_size",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_cache_size",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("cache_size"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("bus_speed"): AttributeDisplayHint(
                        name="inv_hardware_cpu_bus_speed",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_bus_speed",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("bus_speed"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("voltage"): AttributeDisplayHint(
                        name="inv_hardware_cpu_voltage",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_voltage",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("voltage"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("sharing_mode"): AttributeDisplayHint(
                        name="inv_hardware_cpu_sharing_mode",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_sharing_mode",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("sharing_mode"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("implementation_mode"): AttributeDisplayHint(
                        name="inv_hardware_cpu_implementation_mode",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_implementation_mode",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("implementation_mode"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("entitlement"): AttributeDisplayHint(
                        name="inv_hardware_cpu_entitlement",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: ("", ""),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_entitlement",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("entitlement"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                },
                table=Table(columns={}),
            ),
        ),
        (
            ("software", "applications", "docker", "images"),
            NodeDisplayHint(
                name="inv_software_applications_docker_images",
                path=(
                    SDNodeName("software"),
                    SDNodeName("applications"),
                    SDNodeName("docker"),
                    SDNodeName("images"),
                ),
                icon="",
                title="Docker images",
                short_title="Docker images",
                long_title="Docker ➤ Docker images",
                attributes={},
                # The single column hints are not checked here
                table=TableWithView(
                    columns={
                        SDKey("id"): ColumnDisplayHintOfView(
                            name="invdockerimages_id",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_id",
                                title="",
                            ),
                        ),
                        SDKey("creation"): ColumnDisplayHintOfView(
                            name="invdockerimages_creation",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_creation",
                                title="",
                            ),
                        ),
                        SDKey("size"): ColumnDisplayHintOfView(
                            name="invdockerimages_size",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_size",
                                title="",
                            ),
                        ),
                        SDKey("labels"): ColumnDisplayHintOfView(
                            name="invdockerimages_labels",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_labels",
                                title="",
                            ),
                        ),
                        SDKey("amount_containers"): ColumnDisplayHintOfView(
                            name="invdockerimages_amount_containers",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_amount_containers",
                                title="",
                            ),
                        ),
                        SDKey("repotags"): ColumnDisplayHintOfView(
                            name="invdockerimages_repotags",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_repotags",
                                title="",
                            ),
                        ),
                        SDKey("repodigests"): ColumnDisplayHintOfView(
                            name="invdockerimages_repodigests",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_repodigests",
                                title="",
                            ),
                        ),
                    },
                    name="invdockerimages",
                    path=(
                        SDNodeName("software"),
                        SDNodeName("applications"),
                        SDNodeName("docker"),
                        SDNodeName("images"),
                    ),
                    long_title="Docker ➤ Docker images",
                    icon="",
                    is_show_more=False,
                ),
            ),
        ),
        (
            ("path", "to", "node"),
            NodeDisplayHint(
                name="inv_path_to_node",
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                icon="",
                title="Node",
                short_title="Node",
                long_title="To ➤ Node",
                attributes={},
                table=Table(columns={}),
            ),
        ),
    ],
)
def test_make_node_displayhint(path: SDPath, expected_node_hint: NodeDisplayHint) -> None:
    node_hint = inv_display_hints.get_node_hint(path)

    assert node_hint.name == expected_node_hint.name
    assert node_hint.icon == expected_node_hint.icon
    assert node_hint.title == expected_node_hint.title
    assert node_hint.long_title == expected_node_hint.long_title
    assert node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert list(node_hint.attributes) == list(expected_node_hint.attributes)
    assert list(node_hint.table.columns) == list(expected_node_hint.table.columns)

    if isinstance(expected_node_hint.table, TableWithView):
        assert isinstance(node_hint.table, TableWithView)
        assert node_hint.table.name == expected_node_hint.table.name
        assert node_hint.table.path == expected_node_hint.table.path
        assert node_hint.table.long_title == expected_node_hint.table.long_title
        assert node_hint.table.icon == expected_node_hint.table.icon
        assert node_hint.table.is_show_more == expected_node_hint.table.is_show_more


@pytest.mark.parametrize(
    "raw_path, expected_node_hint",
    [
        (
            ".foo.bar.",
            NodeDisplayHint(
                name="invfoo_bar",
                path=(SDNodeName("foo"), SDNodeName("bar")),
                icon="",
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ".foo.bar:",
            NodeDisplayHint(
                name="invfoo_bar",
                path=(SDNodeName("foo"), SDNodeName("bar")),
                icon="",
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ".software.",
            NodeDisplayHint(
                name="invsoftware",
                path=(SDNodeName("software"),),
                icon="software",
                title="Software",
                short_title="Software",
                long_title="Software",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ".software.applications.docker.containers:",
            NodeDisplayHint(
                name="invsoftware_applications_docker_containers",
                path=(
                    SDNodeName("software"),
                    SDNodeName("applications"),
                    SDNodeName("docker"),
                    SDNodeName("containers"),
                ),
                icon="",
                title="Docker containers",
                short_title="Docker containers",
                long_title="Docker ➤ Docker containers",
                attributes={},
                # The single column hints are not checked here
                table=TableWithView(
                    columns={
                        SDKey("id"): ColumnDisplayHintOfView(
                            name="invdockercontainers_id",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_id",
                                title="",
                            ),
                        ),
                        SDKey("creation"): ColumnDisplayHintOfView(
                            name="invdockercontainers_creation",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_creation",
                                title="",
                            ),
                        ),
                        SDKey("name"): ColumnDisplayHintOfView(
                            name="invdockercontainers_name",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_name",
                                title="",
                            ),
                        ),
                        SDKey("labels"): ColumnDisplayHintOfView(
                            name="invdockercontainers_labels",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_labels",
                                title="",
                            ),
                        ),
                        SDKey("status"): ColumnDisplayHintOfView(
                            name="invdockercontainers_status",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_status",
                                title="",
                            ),
                        ),
                        SDKey("image"): ColumnDisplayHintOfView(
                            name="invdockercontainers_image",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: ("", ""),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_image",
                                title="",
                            ),
                        ),
                    },
                    name="invdockercontainers",
                    path=(
                        SDNodeName("software"),
                        SDNodeName("applications"),
                        SDNodeName("docker"),
                        SDNodeName("containers"),
                    ),
                    long_title="Docker ➤ Docker containers",
                    icon="",
                    is_show_more=False,
                ),
            ),
        ),
    ],
)
def test_make_node_displayhint_from_hint(
    raw_path: str, expected_node_hint: NodeDisplayHint
) -> None:
    node_hint = inv_display_hints.get_node_hint(
        cmk.gui.inventory.parse_internal_raw_path(raw_path).path
    )

    assert node_hint.name == "_".join(("inv",) + node_hint.path)
    assert node_hint.icon == expected_node_hint.icon
    assert node_hint.title == expected_node_hint.title
    assert node_hint.long_title == expected_node_hint.long_title
    assert node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert list(node_hint.attributes) == list(expected_node_hint.attributes)
    assert list(node_hint.table.columns) == list(expected_node_hint.table.columns)

    if isinstance(expected_node_hint.table, TableWithView):
        assert isinstance(node_hint.table, TableWithView)
        assert node_hint.table.name == expected_node_hint.table.name
        assert node_hint.table.path == expected_node_hint.table.path
        assert node_hint.table.long_title == expected_node_hint.table.long_title
        assert node_hint.table.icon == expected_node_hint.table.icon
        assert node_hint.table.is_show_more == expected_node_hint.table.is_show_more


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            (),
            "key",
            ColumnDisplayHint(
                title="Key",
                short_title="Key",
                long_title="Key",
                paint_function=inv_paint_generic,
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            ColumnDisplayHint(
                title="Key",
                short_title="Key",
                long_title="Node ➤ Key",
                paint_function=inv_paint_generic,
            ),
        ),
    ],
)
def test_make_column_displayhint(path: SDPath, key: str, expected: ColumnDisplayHint) -> None:
    hint = inv_display_hints.get_node_hint(path).get_column_hint(key)
    assert isinstance(hint, ColumnDisplayHint)
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            ("networking", "interfaces"),
            "oper_status",
            ColumnDisplayHintOfView(
                name="invinterface_oper_status",
                title="Operational status",
                short_title="Operational status",
                long_title="Network interfaces ➤ Operational status",
                paint_function=inv_paint_if_oper_status,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvtableText(
                    inv_info="invinterface",
                    ident="invinterface_oper_status",
                    title="Network interfaces ➤ Operational status",
                ),
            ),
        ),
        (
            ("software", "applications", "check_mk", "sites"),
            "cmc",
            ColumnDisplayHintOfView(
                name="invcmksites_cmc",
                title="CMC status",
                short_title="CMC",
                long_title="Checkmk sites ➤ CMC status",
                paint_function=inv_paint_service_status,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvtableText(
                    inv_info="invcmksites",
                    ident="invcmksites_cmc",
                    title="Checkmk sites ➤ CMC status",
                ),
            ),
        ),
    ],
)
def test_make_column_displayhint_of_view(
    path: SDPath, key: str, expected: ColumnDisplayHintOfView
) -> None:
    hint = inv_display_hints.get_node_hint(path).get_column_hint(key)
    assert isinstance(hint, ColumnDisplayHintOfView)
    assert hint.name == expected.name
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.filter is not None
    assert hint.filter.ident == expected.filter.ident
    assert hint.filter.title == expected.filter.title
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo:*.bar",
            ColumnDisplayHint(
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                paint_function=inv_paint_generic,
            ),
        ),
    ],
)
def test_make_column_displayhint_from_hint(raw_path: str, expected: ColumnDisplayHint) -> None:
    inventory_path = cmk.gui.inventory.parse_internal_raw_path(raw_path)
    hint = inv_display_hints.get_node_hint(inventory_path.path).get_column_hint(
        inventory_path.key or ""
    )
    assert isinstance(hint, ColumnDisplayHint)
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".software.packages:*.package_version",
            ColumnDisplayHintOfView(
                name="invswpac_package_version",
                title="Package version",
                short_title="Package version",
                long_title="Software packages ➤ Package version",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(cmp_version),
                filter=FilterInvtableText(
                    inv_info="invswpac",
                    ident="invswpac_package_version",
                    title="Software packages ➤ Package version",
                ),
            ),
        ),
        (
            ".software.packages:*.version",
            ColumnDisplayHintOfView(
                name="invswpac_version",
                title="Version",
                short_title="Version",
                long_title="Software packages ➤ Version",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(cmp_version),
                filter=FilterInvtableText(
                    inv_info="invswpac",
                    ident="invswpac_version",
                    title="Software packages ➤ Version",
                ),
            ),
        ),
        (
            ".networking.interfaces:*.index",
            ColumnDisplayHintOfView(
                name="invinterface_index",
                title="Index",
                short_title="Index",
                long_title="Network interfaces ➤ Index",
                paint_function=inv_paint_number,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvtableText(
                    inv_info="invinterface",
                    ident="invinterface_index",
                    title="Network interfaces ➤ Index",
                ),
            ),
        ),
        (
            ".networking.interfaces:*.oper_status",
            ColumnDisplayHintOfView(
                name="invinterface_oper_status",
                title="Operational status",
                short_title="Operational status",
                long_title="Network interfaces ➤ Operational status",
                paint_function=inv_paint_if_oper_status,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvtableText(
                    inv_info="invinterface",
                    ident="invinterface_oper_status",
                    title="Network interfaces ➤ Operational status",
                ),
            ),
        ),
    ],
)
def test_make_column_displayhint_of_view_from_hint(
    raw_path: str, expected: ColumnDisplayHintOfView
) -> None:
    inventory_path = cmk.gui.inventory.parse_internal_raw_path(raw_path)
    hint = inv_display_hints.get_node_hint(inventory_path.path).get_column_hint(
        inventory_path.key or ""
    )
    assert isinstance(hint, ColumnDisplayHintOfView)
    assert hint.name == expected.name
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.filter is not None
    assert hint.filter.ident == expected.filter.ident
    assert hint.filter.title == expected.filter.title
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            (),
            "key",
            AttributeDisplayHint(
                name="inv_key",
                title="Key",
                short_title="Key",
                long_title="Key",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_key",
                    title="Key",
                    inventory_path=InventoryPath(
                        path=(),
                        source=TreeSource.attributes,
                        key=SDKey("key"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ("hardware", "storage", "disks"),
            "size",
            AttributeDisplayHint(
                name="inv_hardware_storage_disks_size",
                title="Size",
                short_title="Size",
                long_title="Block devices ➤ Size",
                paint_function=inv_paint_size,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_hardware_storage_disks_size",
                    title="Block devices ➤ Size",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("hardware"), SDNodeName("storage"), SDNodeName("disks")),
                        source=TreeSource.attributes,
                        key=SDKey("size"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            AttributeDisplayHint(
                name="inv_path_to_node_key",
                title="Key",
                short_title="Key",
                long_title="Node ➤ Key",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_path_to_node_key",
                    title="Node ➤ Key",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                        source=TreeSource.attributes,
                        key=SDKey("key"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
    ],
)
def test_make_attribute_displayhint(path: SDPath, key: str, expected: AttributeDisplayHint) -> None:
    hint = inv_display_hints.get_node_hint(path).get_attribute_hint(key)
    assert hint.name == expected.name
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.filter.ident == expected.filter.ident
    assert hint.filter.title == expected.filter.title
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo.bar",
            AttributeDisplayHint(
                name="inv_foo_bar",
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_foo_bar",
                    title="Foo ➤ Bar",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("foo"),),
                        source=TreeSource.attributes,
                        key=SDKey("bar"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ".hardware.cpu.arch",
            AttributeDisplayHint(
                name="inv_hardware_cpu_arch",
                title="CPU architecture",
                short_title="CPU architecture",
                long_title="Processor ➤ CPU architecture",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_hardware_cpu_arch",
                    title="Processor ➤ CPU architecture",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("hardware"), SDNodeName("cpu")),
                        source=TreeSource.attributes,
                        key=SDKey("arch"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ".hardware.system.product",
            AttributeDisplayHint(
                name="inv_hardware_system_product",
                title="Product",
                short_title="Product",
                long_title="System ➤ Product",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_hardware_system_product",
                    title="System ➤ Product",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("hardware"), SDNodeName("system")),
                        source=TreeSource.attributes,
                        key=SDKey("product"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
    ],
)
def test_make_attribute_displayhint_from_hint(
    raw_path: str, expected: AttributeDisplayHint
) -> None:
    inventory_path = cmk.gui.inventory.parse_internal_raw_path(raw_path)
    hint = inv_display_hints.get_node_hint(inventory_path.path).get_attribute_hint(
        inventory_path.key or ""
    )
    assert hint.name == expected.name
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.filter.ident == expected.filter.ident
    assert hint.filter.title == expected.filter.title
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "view_name, expected_view_name",
    [
        ("", ""),
        ("viewname", "invviewname"),
        ("invviewname", "invviewname"),
        ("viewname_of_host", "invviewname"),
        ("invviewname_of_host", "invviewname"),
    ],
)
def test__parse_view_name(view_name: str, expected_view_name: str) -> None:
    assert _parse_view_name(view_name) == expected_view_name


def test_render_bool() -> None:
    bool_field = BoolFieldFromAPI(
        TitleFromAPI("A title"),
        render_true=LabelFromAPI("It's true"),
        render_false=LabelFromAPI("It's false"),
    )
    assert _PaintBool(bool_field)(True) == (
        "",
        HTML(
            "<div style=\"text-align: left\"><span style=''>It&#x27;s true</span></div>",
            escape=False,
        ),
    )
    assert _PaintBool(bool_field)(False) == (
        "",
        HTML(
            "<div style=\"text-align: left\"><span style=''>It&#x27;s false</span></div>",
            escape=False,
        ),
    )


@pytest.mark.parametrize(
    ["render", "value", "expected"],
    [
        pytest.param(lambda v: "one" if v == 1 else "more", 1, "one", id="Callable"),
        pytest.param(
            UnitFromAPI(notation=DecimalNotationFromAPI("count")),
            1.00,
            "1 count",
            id="DecimalNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=SINotationFromAPI("B")),
            1000,
            "1 kB",
            id="SINotation",
        ),
        pytest.param(
            UnitFromAPI(notation=IECNotationFromAPI("bits")),
            1024,
            "1 Kibits",
            id="IECNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=StandardScientificNotationFromAPI("snakes")),
            1000,
            "1e+3 snakes",
            id="StandardScientificNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=TimeNotationFromAPI()),
            60,
            "1 min",
            id="TimeNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=AgeNotationFromAPI()),
            datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.UTC).timestamp(),
            "1 min",
            id="AgeNotation",
        ),
    ],
)
def test_render_number(
    render: Callable[[int | float], LabelFromAPI | str] | UnitFromAPI,
    value: int | float,
    expected: str,
) -> None:
    number_field = NumberFieldFromAPI(
        TitleFromAPI("A title"), render=render, style=lambda _: [AlignmentFromAPI.CENTERED]
    )
    now = datetime.datetime(2025, 1, 1, 0, 1, 0, tzinfo=datetime.UTC).timestamp()
    assert _PaintNumber(number_field)(value, now) == (
        "",
        HTML(
            f"<div style=\"text-align: center\"><span style=''>{expected}</span></div>",
            escape=False,
        ),
    )


def test_render_text() -> None:
    text_field = TextFieldFromAPI(
        TitleFromAPI("A title"),
        render=lambda v: f"hello {v}",
        style=lambda _: [LabelColorFromAPI.PINK],
    )
    assert _PaintText(text_field)("world") == (
        "",
        HTML(
            '<div style="text-align: left"><span style="color: #ff64ff">hello world</span></div>',
            escape=False,
        ),
    )


def test_render_choice() -> None:
    choice_field = ChoiceFieldFromAPI(
        TitleFromAPI("A title"),
        mapping={1: LabelFromAPI("One")},
    )
    assert _PaintChoice(choice_field)(1) == (
        "",
        HTML("<div style=\"text-align: center\"><span style=''>One</span></div>", escape=False),
    )
    assert _PaintChoice(choice_field)(2) == (
        "",
        HTML(
            "<div style=\"text-align: center\"><span style=''>&lt;2&gt; (No such value)</span></div>",
            escape=False,
        ),
    )


def test_sort_text() -> None:
    text_field = TextFieldFromAPI(TitleFromAPI("A title"), sort_key=int)
    assert _decorate_sort_function(_SortFunctionText(text_field))("1", "2") == -1
    assert _decorate_sort_function(_SortFunctionText(text_field))("2", "1") == 1


def test_sort_choice() -> None:
    choice_field = ChoiceFieldFromAPI(
        TitleFromAPI("A title"),
        mapping={
            2: LabelFromAPI("Two"),
            1: LabelFromAPI("One"),
        },
    )
    assert _decorate_sort_function(_SortFunctionChoice(choice_field))(1, 2) == 1
    assert _decorate_sort_function(_SortFunctionChoice(choice_field))(2, 1) == -1

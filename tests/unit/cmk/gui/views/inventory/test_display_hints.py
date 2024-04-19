#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# No stub file
import pytest

from cmk.utils.structured_data import SDPath

import cmk.gui.inventory
import cmk.gui.utils
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.http import request, response
from cmk.gui.inventory.filters import FilterInvtableText, FilterInvtableVersion
from cmk.gui.logged_in import user
from cmk.gui.num_split import cmp_version
from cmk.gui.painter.v0.helpers import RenderLink
from cmk.gui.painter_options import PainterOptions
from cmk.gui.utils.theme import theme
from cmk.gui.views.inventory import (
    _register_sorter,
    inv_paint_generic,
    inv_paint_if_oper_status,
    inv_paint_number,
    inv_paint_service_status,
    inv_paint_size,
)
from cmk.gui.views.inventory._display_hints import (
    _cmp_inv_generic,
    _decorate_sort_function,
    _get_related_raw_hints,
    _RelatedRawHints,
    AttributeDisplayHint,
    AttributesDisplayHint,
    ColumnDisplayHint,
    DISPLAY_HINTS,
    NodeDisplayHint,
    TableDisplayHint,
    TableViewSpec,
)
from cmk.gui.views.inventory.registry import inventory_displayhints
from cmk.gui.views.sorter import sorter_registry


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

    all_related_raw_hints = _get_related_raw_hints(inventory_displayhints)

    def _check_path(path: SDPath) -> bool:
        return all(path[:idx] in all_related_raw_hints for idx in range(1, len(path)))

    def _check_raw_hints(related_raw_hints: _RelatedRawHints) -> bool:
        return bool(related_raw_hints.for_node) ^ bool(related_raw_hints.for_table)

    def _check_table_key_order(path: SDPath, related_raw_hints: _RelatedRawHints) -> bool:
        ignored_keys = set(_IGNORED_KEYS_BY_PATH.get(path, []))
        return (
            set(related_raw_hints.for_table.get("keyorder", [])) - ignored_keys
            == set(related_raw_hints.by_columns) - ignored_keys
        )

    def _check_attributes_key_order(path: SDPath, related_raw_hints: _RelatedRawHints) -> bool:
        ignored_keys = set(_IGNORED_KEYS_BY_PATH.get(path, []))
        return (
            set(related_raw_hints.for_node.get("keyorder", [])) - ignored_keys
            == set(related_raw_hints.by_attributes) - ignored_keys
        )

    assert all(
        _check_path(path)
        and _check_raw_hints(related_raw_hints)
        and _check_table_key_order(path, related_raw_hints)
        and _check_attributes_key_order(path, related_raw_hints)
        for path, related_raw_hints in _get_related_raw_hints(inventory_displayhints).items()
    )


def test_missing_table_keyorder() -> None:
    ignore_paths = [
        ".hardware.memory.arrays:",  # Has no table
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
    "path, expected_node_hint, expected_attributes_hint, expected_table_hint",
    [
        (
            tuple(),
            NodeDisplayHint(
                icon=None,
                title="Inventory Tree",
                _long_title_function=lambda: "Inventory Tree",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ("hardware",),
            NodeDisplayHint(
                icon="hardware",
                title="Hardware",
                _long_title_function=lambda: "Hardware",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ("hardware", "cpu"),
            NodeDisplayHint(
                icon=None,
                title="Processor",
                _long_title_function=lambda: "Hardware ➤ Processor",
            ),
            AttributesDisplayHint(
                key_order=[
                    "arch",
                    "max_speed",
                    "model",
                    "type",
                    "threads",
                    "smt_threads",
                    "cpu_max_capa",
                    "cpus",
                    "logical_cpus",
                    "cores",
                    "cores_per_cpu",
                    "threads_per_cpu",
                    "cache_size",
                    "bus_speed",
                    "voltage",
                    "sharing_mode",
                    "implementation_mode",
                    "entitlement",
                ],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ("software", "applications", "docker", "images"),
            NodeDisplayHint(
                icon=None,
                title="Docker images",
                _long_title_function=lambda: "Docker ➤ Docker images",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[
                    "id",
                    "creation",
                    "size",
                    "labels",
                    "amount_containers",
                    "repotags",
                    "repodigests",
                ],
                is_show_more=False,
                view_spec=TableViewSpec(
                    view_name="invdockerimages",
                    title="Docker images",
                    _long_title_function=lambda: "Docker ➤ Docker images",
                    icon=None,
                ),
            ),
        ),
        (
            ("path", "to", "node"),
            NodeDisplayHint(
                icon=None,
                title="Node",
                _long_title_function=lambda: "To ➤ Node",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
    ],
)
def test_make_node_displayhint(
    path: SDPath,
    expected_node_hint: NodeDisplayHint,
    expected_attributes_hint: AttributesDisplayHint,
    expected_table_hint: TableDisplayHint,
) -> None:
    hints = DISPLAY_HINTS.get_tree_hints(path)

    assert hints.node_hint.icon == expected_node_hint.icon
    assert hints.node_hint.title == expected_node_hint.title
    assert hints.node_hint.long_title == expected_node_hint.long_title
    assert hints.node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert hints.attributes_hint.key_order == expected_attributes_hint.key_order

    assert hints.table_hint.key_order == expected_table_hint.key_order
    assert hints.table_hint.is_show_more == expected_table_hint.is_show_more

    if expected_table_hint.view_spec:
        assert hints.table_hint.view_spec is not None
        assert hints.table_hint.view_spec.long_title == expected_table_hint.view_spec.long_title
        assert (
            hints.table_hint.view_spec.long_inventory_title
            == expected_table_hint.view_spec.long_inventory_title
        )


@pytest.mark.parametrize(
    "raw_path, expected_node_hint, expected_attributes_hint, expected_table_hint",
    [
        (
            ".foo.bar.",
            NodeDisplayHint(
                icon=None,
                title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ".foo.bar:",
            NodeDisplayHint(
                icon=None,
                title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ".software.",
            NodeDisplayHint(
                icon="software",
                title="Software",
                _long_title_function=lambda: "Software",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ".software.applications.docker.containers:",
            NodeDisplayHint(
                icon=None,
                title="Docker containers",
                _long_title_function=lambda: "Docker ➤ Docker containers",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=["id", "creation", "name", "labels", "status", "image"],
                is_show_more=False,
                view_spec=TableViewSpec(
                    view_name="invdockercontainers",
                    title="Docker containers",
                    _long_title_function=lambda: "Docker ➤ Docker containers",
                    icon=None,
                ),
            ),
        ),
    ],
)
def test_make_node_displayhint_from_hint(
    raw_path: str,
    expected_node_hint: NodeDisplayHint,
    expected_attributes_hint: AttributesDisplayHint,
    expected_table_hint: TableDisplayHint,
) -> None:
    hints = DISPLAY_HINTS.get_tree_hints(cmk.gui.inventory.InventoryPath.parse(raw_path).path)

    assert hints.node_hint.icon == expected_node_hint.icon
    assert hints.node_hint.title == expected_node_hint.title
    assert hints.node_hint.long_title == expected_node_hint.long_title
    assert hints.node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert hints.attributes_hint.key_order == expected_attributes_hint.key_order

    assert hints.table_hint.key_order == expected_table_hint.key_order
    assert hints.table_hint.is_show_more == expected_table_hint.is_show_more

    if expected_table_hint.view_spec:
        assert hints.table_hint.view_spec is not None
        assert hints.table_hint.view_spec.long_title == expected_table_hint.view_spec.long_title
        assert (
            hints.table_hint.view_spec.long_inventory_title
            == expected_table_hint.view_spec.long_inventory_title
        )


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            tuple(),
            "key",
            ColumnDisplayHint(
                paint_function=inv_paint_generic,
                title="Key",
                short=None,
                _long_title_function=lambda: "Key",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ("networking", "interfaces"),
            "oper_status",
            ColumnDisplayHint(
                paint_function=inv_paint_if_oper_status,
                title="Operational Status",
                short=None,
                _long_title_function=lambda: "Network interfaces ➤ Operational Status",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            ColumnDisplayHint(
                paint_function=inv_paint_generic,
                title="Key",
                short=None,
                _long_title_function=lambda: "Node ➤ Key",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ("software", "applications", "check_mk", "sites"),
            "cmc",
            ColumnDisplayHint(
                paint_function=inv_paint_service_status,
                title="CMC status",
                short="CMC",
                _long_title_function=lambda: "Checkmk sites ➤ CMC status",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
    ],
)
def test_make_column_displayhint(path: SDPath, key: str, expected: ColumnDisplayHint) -> None:
    hint = DISPLAY_HINTS.get_tree_hints(path).get_column_hint(key)

    assert hint.title == expected.title
    assert hint.short == expected.short
    assert hint.long_title == expected.long_title
    assert hint.long_inventory_title == expected.long_inventory_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo:*.bar",
            ColumnDisplayHint(
                paint_function=inv_paint_generic,
                title="Bar",
                short=None,
                _long_title_function=lambda: "Foo ➤ Bar",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ".software.packages:*.package_version",
            ColumnDisplayHint(
                paint_function=inv_paint_generic,
                title="Package Version",
                short=None,
                _long_title_function=lambda: "Software packages ➤ Package Version",
                sort_function=_decorate_sort_function(cmp_version),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ".software.packages:*.version",
            ColumnDisplayHint(
                paint_function=inv_paint_generic,
                title="Version",
                short=None,
                _long_title_function=lambda: "Software packages ➤ Version",
                sort_function=_decorate_sort_function(cmp_version),
                filter_class=FilterInvtableVersion,
            ),
        ),
        (
            ".networking.interfaces:*.index",
            ColumnDisplayHint(
                paint_function=inv_paint_number,
                title="Index",
                short=None,
                _long_title_function=lambda: "Network interfaces ➤ Index",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ".networking.interfaces:*.oper_status",
            ColumnDisplayHint(
                paint_function=inv_paint_if_oper_status,
                title="Operational Status",
                short=None,
                _long_title_function=lambda: "Network interfaces ➤ Operational Status",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
    ],
)
def test_make_column_displayhint_from_hint(raw_path: str, expected: ColumnDisplayHint) -> None:
    inventory_path = cmk.gui.inventory.InventoryPath.parse(raw_path)
    hint = DISPLAY_HINTS.get_tree_hints(inventory_path.path).get_column_hint(
        inventory_path.key or ""
    )

    assert hint.title == expected.title
    assert hint.long_title == expected.long_title
    assert hint.long_inventory_title == expected.long_inventory_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            tuple(),
            "key",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Key",
                short=None,
                _long_title_function=lambda: "Key",
                is_show_more=True,
            ),
        ),
        (
            ("hardware", "storage", "disks"),
            "size",
            AttributeDisplayHint(
                data_type="size",
                paint_function=inv_paint_size,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Size",
                short=None,
                _long_title_function=lambda: "Block Devices ➤ Size",
                is_show_more=True,
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Key",
                short=None,
                _long_title_function=lambda: "Node ➤ Key",
                is_show_more=True,
            ),
        ),
    ],
)
def test_make_attribute_displayhint(path: SDPath, key: str, expected: AttributeDisplayHint) -> None:
    hint = DISPLAY_HINTS.get_tree_hints(path).get_attribute_hint(key)

    assert hint.data_type == expected.data_type
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.title == expected.title
    assert hint.long_title == expected.long_title
    assert hint.long_inventory_title == expected.long_inventory_title
    assert hint.is_show_more == expected.is_show_more


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo.bar",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Bar",
                short=None,
                _long_title_function=lambda: "Foo ➤ Bar",
                is_show_more=True,
            ),
        ),
        (
            ".hardware.cpu.arch",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="CPU Architecture",
                short=None,
                _long_title_function=lambda: "Processor ➤ CPU Architecture",
                is_show_more=True,
            ),
        ),
        (
            ".hardware.system.product",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Product",
                short=None,
                _long_title_function=lambda: "System ➤ Product",
                is_show_more=False,
            ),
        ),
    ],
)
def test_make_attribute_displayhint_from_hint(
    raw_path: str, expected: AttributeDisplayHint
) -> None:
    inventory_path = cmk.gui.inventory.InventoryPath.parse(raw_path)
    hint = DISPLAY_HINTS.get_tree_hints(inventory_path.path).get_attribute_hint(
        inventory_path.key or ""
    )

    assert hint.data_type == expected.data_type
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.title == expected.title
    assert hint.long_title == expected.long_title
    assert hint.long_inventory_title == expected.long_inventory_title
    assert hint.is_show_more == expected.is_show_more


@pytest.mark.parametrize(
    "abc_path, path, expected_title",
    [
        (
            ("software", "applications", "vmwareesx", "*"),
            ("software", "applications", "vmwareesx", "1"),
            "Datacenter 1",
        ),
        (
            ("software", "applications", "vmwareesx", "*", "clusters", "*"),
            ("software", "applications", "vmwareesx", "1", "clusters", "2"),
            "Cluster 2",
        ),
    ],
)
def test_replace_placeholder(abc_path: SDPath, path: SDPath, expected_title: str) -> None:
    assert DISPLAY_HINTS.get_tree_hints(abc_path).replace_placeholders(path) == expected_title


@pytest.mark.parametrize(
    "view_name, expected",
    [
        ("viewname", "invviewname"),
        ("invviewname", "invviewname"),
    ],
)
def test_view_spec_view_name(view_name: str, expected: str) -> None:
    table_view_spec = TableViewSpec.from_raw(tuple(), {"view": view_name})
    assert table_view_spec is not None
    assert table_view_spec.view_name == expected


def test_registered_sorter_cmp() -> None:
    hint = AttributeDisplayHint(
        data_type="str",
        paint_function=inv_paint_generic,
        sort_function=_decorate_sort_function(_cmp_inv_generic),
        title="Product",
        short=None,
        _long_title_function=lambda: "System ➤ Product",
        is_show_more=False,
    )

    _register_sorter(
        ident="test_sorter",
        long_inventory_title="A long title",
        load_inv=False,
        columns=["foobar"],
        hint=hint,
        value_extractor=lambda v: v.get("key"),
    )

    sorter_cls = sorter_registry.get("test_sorter")
    assert sorter_cls is not None
    assert (
        sorter_cls(
            user=user,
            config=active_config,
            request=request,
            painter_options=PainterOptions.get_instance(),
            theme=theme,
            url_renderer=RenderLink(request, response, display_options),
        ).cmp({}, {}, None)
        == 0
    )

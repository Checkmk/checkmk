#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import OrderedDict

# No stub file
import pytest

from cmk.utils.structured_data import SDKey, SDNodeName, SDPath

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
from cmk.gui.views.inventory import _register_sorter
from cmk.gui.views.inventory._display_hints import (
    _cmp_inv_generic,
    _decorate_sort_function,
    _get_related_raw_hints,
    _parse_view_name,
    _RelatedRawHints,
    AttributeDisplayHint,
    AttributesDisplayHint,
    ColumnDisplayHint,
    DISPLAY_HINTS,
    NodeDisplayHint,
    TableDisplayHint,
)
from cmk.gui.views.inventory._paint_functions import (
    inv_paint_generic,
    inv_paint_if_oper_status,
    inv_paint_number,
    inv_paint_service_status,
    inv_paint_size,
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
            == set(related_raw_hints.by_column) - ignored_keys
        )

    def _check_attributes_key_order(path: SDPath, related_raw_hints: _RelatedRawHints) -> bool:
        ignored_keys = set(_IGNORED_KEYS_BY_PATH.get(path, []))
        return (
            set(related_raw_hints.for_node.get("keyorder", [])) - ignored_keys
            == set(related_raw_hints.by_key) - ignored_keys
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
                path=tuple(),
                icon="",
                title="Inventory Tree",
                short_title="Inventory Tree",
                _long_title_function=lambda: "Inventory Tree",
            ),
            AttributesDisplayHint(OrderedDict()),
            TableDisplayHint(
                title="",
                _long_title_function=lambda: "",
                icon="",
                is_show_more=True,
                view_name="",
                by_column=OrderedDict(),
            ),
        ),
        (
            ("hardware",),
            NodeDisplayHint(
                path=(SDNodeName("hardware"),),
                icon="hardware",
                title="Hardware",
                short_title="Hardware",
                _long_title_function=lambda: "Hardware",
            ),
            AttributesDisplayHint(OrderedDict()),
            TableDisplayHint(
                title="Hardware",
                _long_title_function=lambda: "Hardware",
                icon="hardware",
                is_show_more=True,
                view_name="",
                by_column=OrderedDict(),
            ),
        ),
        (
            ("hardware", "cpu"),
            NodeDisplayHint(
                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                icon="",
                title="Processor",
                short_title="Processor",
                _long_title_function=lambda: "Hardware ➤ Processor",
            ),
            AttributesDisplayHint(
                # The single attribute hints are not checked here
                OrderedDict(
                    arch=AttributeDisplayHint.from_raw(tuple(), "arch", {}),
                    max_speed=AttributeDisplayHint.from_raw(tuple(), "max_speed", {}),
                    model=AttributeDisplayHint.from_raw(tuple(), "model", {}),
                    type=AttributeDisplayHint.from_raw(tuple(), "type", {}),
                    threads=AttributeDisplayHint.from_raw(tuple(), "threads", {}),
                    smt_threads=AttributeDisplayHint.from_raw(tuple(), "smt_threads", {}),
                    cpu_max_capa=AttributeDisplayHint.from_raw(tuple(), "cpu_max_capa", {}),
                    cpus=AttributeDisplayHint.from_raw(tuple(), "cpus", {}),
                    logical_cpus=AttributeDisplayHint.from_raw(tuple(), "logical_cpus", {}),
                    cores=AttributeDisplayHint.from_raw(tuple(), "cores", {}),
                    cores_per_cpu=AttributeDisplayHint.from_raw(tuple(), "cores_per_cpu", {}),
                    threads_per_cpu=AttributeDisplayHint.from_raw(tuple(), "threads_per_cpu", {}),
                    cache_size=AttributeDisplayHint.from_raw(tuple(), "cache_size", {}),
                    bus_speed=AttributeDisplayHint.from_raw(tuple(), "bus_speed", {}),
                    voltage=AttributeDisplayHint.from_raw(tuple(), "voltage", {}),
                    sharing_mode=AttributeDisplayHint.from_raw(tuple(), "sharing_mode", {}),
                    implementation_mode=AttributeDisplayHint.from_raw(
                        tuple(), "implementation_mode", {}
                    ),
                    entitlement=AttributeDisplayHint.from_raw(tuple(), "entitlement", {}),
                )
            ),
            TableDisplayHint(
                title="Processor",
                _long_title_function=lambda: "Hardware ➤ Processor",
                icon="",
                is_show_more=True,
                view_name="",
                by_column=OrderedDict(),
            ),
        ),
        (
            ("software", "applications", "docker", "images"),
            NodeDisplayHint(
                path=(
                    SDNodeName("software"),
                    SDNodeName("applications"),
                    SDNodeName("docker"),
                    SDNodeName("images"),
                ),
                icon="",
                title="Docker images",
                short_title="Docker images",
                _long_title_function=lambda: "Docker ➤ Docker images",
            ),
            AttributesDisplayHint(OrderedDict()),
            TableDisplayHint(
                title="Docker images",
                _long_title_function=lambda: "Docker ➤ Docker images",
                icon="",
                is_show_more=False,
                view_name="invdockerimages",
                # The single column hints are not checked here
                by_column=OrderedDict(
                    id=ColumnDisplayHint.from_raw("", tuple(), "id", {}),
                    creation=ColumnDisplayHint.from_raw("", tuple(), "creation", {}),
                    size=ColumnDisplayHint.from_raw("", tuple(), "size", {}),
                    labels=ColumnDisplayHint.from_raw("", tuple(), "labels", {}),
                    amount_containers=ColumnDisplayHint.from_raw(
                        "", tuple(), "amount_containers", {}
                    ),
                    repotags=ColumnDisplayHint.from_raw("", tuple(), "repotags", {}),
                    repodigests=ColumnDisplayHint.from_raw("", tuple(), "repodigests", {}),
                ),
            ),
        ),
        (
            ("path", "to", "node"),
            NodeDisplayHint(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                icon="",
                title="Node",
                short_title="Node",
                _long_title_function=lambda: "To ➤ Node",
            ),
            AttributesDisplayHint(OrderedDict()),
            TableDisplayHint(
                title="Node",
                _long_title_function=lambda: "To ➤ Node",
                icon="",
                is_show_more=True,
                view_name="",
                by_column=OrderedDict(),
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

    assert hints.node_hint.ident == "_".join(("inv",) + hints.node_hint.path)
    assert hints.node_hint.icon == expected_node_hint.icon
    assert hints.node_hint.title == expected_node_hint.title
    assert hints.node_hint.long_title == expected_node_hint.long_title
    assert hints.node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert list(hints.attributes_hint.by_key) == list(expected_attributes_hint.by_key)

    assert hints.table_hint.title == expected_table_hint.title
    assert hints.table_hint.long_title == expected_table_hint.long_title
    assert hints.table_hint.long_inventory_title == expected_table_hint.long_inventory_title
    assert hints.table_hint.icon == expected_table_hint.icon
    assert hints.table_hint.is_show_more == expected_table_hint.is_show_more
    assert hints.table_hint.view_name == expected_table_hint.view_name
    assert list(hints.table_hint.by_column) == list(expected_table_hint.by_column)


@pytest.mark.parametrize(
    "raw_path, expected_node_hint, expected_attributes_hint, expected_table_hint",
    [
        (
            ".foo.bar.",
            NodeDisplayHint(
                path=(SDNodeName("foo"), SDNodeName("bar")),
                icon="",
                title="Bar",
                short_title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
            ),
            AttributesDisplayHint(OrderedDict()),
            TableDisplayHint(
                title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
                icon="",
                is_show_more=True,
                view_name="",
                by_column=OrderedDict(),
            ),
        ),
        (
            ".foo.bar:",
            NodeDisplayHint(
                path=(SDNodeName("foo"), SDNodeName("bar")),
                icon="",
                title="Bar",
                short_title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
            ),
            AttributesDisplayHint(OrderedDict()),
            TableDisplayHint(
                title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
                icon="",
                is_show_more=True,
                view_name="",
                by_column=OrderedDict(),
            ),
        ),
        (
            ".software.",
            NodeDisplayHint(
                path=(SDNodeName("software"),),
                icon="software",
                title="Software",
                short_title="Software",
                _long_title_function=lambda: "Software",
            ),
            AttributesDisplayHint(OrderedDict()),
            TableDisplayHint(
                title="Software",
                _long_title_function=lambda: "Software",
                icon="software",
                is_show_more=True,
                view_name="",
                by_column=OrderedDict(),
            ),
        ),
        (
            ".software.applications.docker.containers:",
            NodeDisplayHint(
                path=(
                    SDNodeName("software"),
                    SDNodeName("applications"),
                    SDNodeName("docker"),
                    SDNodeName("containers"),
                ),
                icon="",
                title="Docker containers",
                short_title="Docker containers",
                _long_title_function=lambda: "Docker ➤ Docker containers",
            ),
            AttributesDisplayHint(OrderedDict()),
            TableDisplayHint(
                title="Docker containers",
                _long_title_function=lambda: "Docker ➤ Docker containers",
                icon="",
                is_show_more=False,
                view_name="invdockercontainers",
                # The single column hints are not checked here
                by_column=OrderedDict(
                    id=ColumnDisplayHint.from_raw("", tuple(), "id", {}),
                    creation=ColumnDisplayHint.from_raw("", tuple(), "creation", {}),
                    name=ColumnDisplayHint.from_raw("", tuple(), "name", {}),
                    labels=ColumnDisplayHint.from_raw("", tuple(), "labels", {}),
                    status=ColumnDisplayHint.from_raw("", tuple(), "status", {}),
                    image=ColumnDisplayHint.from_raw("", tuple(), "image", {}),
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

    assert hints.node_hint.ident == "_".join(("inv",) + hints.node_hint.path)
    assert hints.node_hint.icon == expected_node_hint.icon
    assert hints.node_hint.title == expected_node_hint.title
    assert hints.node_hint.long_title == expected_node_hint.long_title
    assert hints.node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert list(hints.attributes_hint.by_key) == list(expected_attributes_hint.by_key)

    assert hints.table_hint.title == expected_table_hint.title
    assert hints.table_hint.long_title == expected_table_hint.long_title
    assert hints.table_hint.long_inventory_title == expected_table_hint.long_inventory_title
    assert hints.table_hint.icon == expected_table_hint.icon
    assert hints.table_hint.is_show_more == expected_table_hint.is_show_more
    assert hints.table_hint.view_name == expected_table_hint.view_name
    assert list(hints.table_hint.by_column) == list(expected_table_hint.by_column)


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            tuple(),
            "key",
            ColumnDisplayHint(
                view_name="",
                key=SDKey("key"),
                paint_function=inv_paint_generic,
                title="Key",
                short_title="Key",
                _long_title_function=lambda: "Key",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ("networking", "interfaces"),
            "oper_status",
            ColumnDisplayHint(
                view_name="invinterface",
                key=SDKey("oper_status"),
                paint_function=inv_paint_if_oper_status,
                title="Operational Status",
                short_title="Operational Status",
                _long_title_function=lambda: "Network interfaces ➤ Operational Status",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            ColumnDisplayHint(
                view_name="",
                key=SDKey("key"),
                paint_function=inv_paint_generic,
                title="Key",
                short_title="Key",
                _long_title_function=lambda: "Node ➤ Key",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ("software", "applications", "check_mk", "sites"),
            "cmc",
            ColumnDisplayHint(
                view_name="",
                key=SDKey("cmc"),
                paint_function=inv_paint_service_status,
                title="CMC status",
                short_title="CMC",
                _long_title_function=lambda: "Checkmk sites ➤ CMC status",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
    ],
)
def test_make_column_displayhint(path: SDPath, key: str, expected: ColumnDisplayHint) -> None:
    hint = DISPLAY_HINTS.get_tree_hints(path).get_column_hint(key)

    if hint.view_name:
        assert hint.ident == f"{hint.view_name}_{hint.key}"
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
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
                view_name="",
                key=SDKey("key"),
                paint_function=inv_paint_generic,
                title="Bar",
                short_title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ".software.packages:*.package_version",
            ColumnDisplayHint(
                view_name="invswpac",
                key=SDKey("package_version"),
                paint_function=inv_paint_generic,
                title="Package Version",
                short_title="Package Version",
                _long_title_function=lambda: "Software packages ➤ Package Version",
                sort_function=_decorate_sort_function(cmp_version),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ".software.packages:*.version",
            ColumnDisplayHint(
                view_name="invswpac",
                key=SDKey("version"),
                paint_function=inv_paint_generic,
                title="Version",
                short_title="Version",
                _long_title_function=lambda: "Software packages ➤ Version",
                sort_function=_decorate_sort_function(cmp_version),
                filter_class=FilterInvtableVersion,
            ),
        ),
        (
            ".networking.interfaces:*.index",
            ColumnDisplayHint(
                view_name="invinterface",
                key=SDKey("index"),
                paint_function=inv_paint_number,
                title="Index",
                short_title="Index",
                _long_title_function=lambda: "Network interfaces ➤ Index",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=FilterInvtableText,
            ),
        ),
        (
            ".networking.interfaces:*.oper_status",
            ColumnDisplayHint(
                view_name="invinterface",
                key=SDKey("oper_status"),
                paint_function=inv_paint_if_oper_status,
                title="Operational Status",
                short_title="Operational Status",
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

    if hint.view_name:
        assert hint.ident == f"{hint.view_name}_{hint.key}"
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
                path=tuple(),
                key=SDKey("key"),
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Key",
                short_title="Key",
                _long_title_function=lambda: "Key",
                is_show_more=True,
            ),
        ),
        (
            ("hardware", "storage", "disks"),
            "size",
            AttributeDisplayHint(
                path=(SDNodeName("hardware"), SDNodeName("storage"), SDNodeName("disks")),
                key=SDKey("size"),
                data_type="size",
                paint_function=inv_paint_size,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Size",
                short_title="Size",
                _long_title_function=lambda: "Block Devices ➤ Size",
                is_show_more=True,
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            AttributeDisplayHint(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                key=SDKey("key"),
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Key",
                short_title="Key",
                _long_title_function=lambda: "Node ➤ Key",
                is_show_more=True,
            ),
        ),
    ],
)
def test_make_attribute_displayhint(path: SDPath, key: str, expected: AttributeDisplayHint) -> None:
    hint = DISPLAY_HINTS.get_tree_hints(path).get_attribute_hint(key)

    assert hint.ident == "_".join(("inv",) + hint.path + (hint.key,))
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
                path=(SDNodeName("foo"),),
                key=SDKey("bar"),
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Bar",
                short_title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
                is_show_more=True,
            ),
        ),
        (
            ".hardware.cpu.arch",
            AttributeDisplayHint(
                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                key=SDKey("arch"),
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="CPU Architecture",
                short_title="CPU Architecture",
                _long_title_function=lambda: "Processor ➤ CPU Architecture",
                is_show_more=True,
            ),
        ),
        (
            ".hardware.system.product",
            AttributeDisplayHint(
                path=(SDNodeName("hardware"), SDNodeName("system")),
                key=SDKey("product"),
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Product",
                short_title="Product",
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

    assert hint.ident == "_".join(("inv",) + hint.path + (hint.key,))
    assert hint.data_type == expected.data_type
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.title == expected.title
    assert hint.long_title == expected.long_title
    assert hint.long_inventory_title == expected.long_inventory_title
    assert hint.is_show_more == expected.is_show_more


@pytest.mark.parametrize(
    "view_name, expected_view_name",
    [
        (None, ""),
        ("", ""),
        ("viewname", "invviewname"),
        ("invviewname", "invviewname"),
        ("viewname_of_host", "invviewname"),
        ("invviewname_of_host", "invviewname"),
    ],
)
def test__parse_view_name(view_name: str | None, expected_view_name: str) -> None:
    assert _parse_view_name(view_name) == expected_view_name


def test_registered_sorter_cmp() -> None:
    hint = AttributeDisplayHint(
        path=tuple(),
        key=SDKey("key"),
        data_type="str",
        paint_function=inv_paint_generic,
        sort_function=_decorate_sort_function(_cmp_inv_generic),
        title="Product",
        short_title="Product",
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

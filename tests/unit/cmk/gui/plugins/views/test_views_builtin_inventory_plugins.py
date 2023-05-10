#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.structured_data import SDPath

from cmk.gui.views.inventory import _RelatedRawHints, DisplayHints, inventory_displayhints


def test_display_hint_titles() -> None:
    assert all("title" in hint for hint in inventory_displayhints.values())


_IGNORED_KEYS_BY_PATH = {
    ("hardware", "system"): ["serial_number", "model_name"],
    ("hardware", "storage", "disks"): [
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

    all_related_raw_hints = DisplayHints._get_related_raw_hints(inventory_displayhints)

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
        for path, related_raw_hints in DisplayHints._get_related_raw_hints(
            inventory_displayhints
        ).items()
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

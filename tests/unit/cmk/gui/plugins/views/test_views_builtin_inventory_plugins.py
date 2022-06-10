#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass, field

from cmk.utils.structured_data import SDPath

from cmk.gui.inventory import InventoryPath, TreeSource
from cmk.gui.plugins.views.builtin_inventory_plugins import inventory_displayhints
from cmk.gui.plugins.views.utils import InventoryHintSpec


def test_display_hint_titles() -> None:
    assert all("title" in hint for hint in inventory_displayhints.values())


@dataclass
class RelatedRawHints:
    for_node: InventoryHintSpec = field(default_factory=dict)
    for_table: InventoryHintSpec = field(default_factory=dict)
    by_columns: dict[str, InventoryHintSpec] = field(default_factory=dict)
    by_attributes: dict[str, InventoryHintSpec] = field(default_factory=dict)


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
    related_raw_hints_by_path: dict[SDPath, RelatedRawHints] = {}
    for raw_path, raw_hint in inventory_displayhints.items():
        inventory_path = InventoryPath.parse(raw_path)
        related_raw_hints = related_raw_hints_by_path.setdefault(
            inventory_path.path,
            RelatedRawHints(),
        )

        if inventory_path.source == TreeSource.node:
            related_raw_hints.for_node.update(raw_hint)
            continue

        if inventory_path.source == TreeSource.table:
            if inventory_path.key:
                related_raw_hints.by_columns.setdefault(inventory_path.key, raw_hint)
                continue

            related_raw_hints.for_table.update(raw_hint)
            continue

        if inventory_path.source == TreeSource.attributes and inventory_path.key:
            related_raw_hints.by_attributes.setdefault(inventory_path.key, raw_hint)
            continue

    assert all(
        bool(related_raw_hints.for_node) or bool(related_raw_hints.for_table)
        for related_raw_hints in related_raw_hints_by_path.values()
    )


def test_missing_table_keyorder() -> None:
    ignore_paths = [
        ".hardware.memory.arrays:",  # Has no table
    ]

    missing_keyorders = [
        path
        for path, hint in inventory_displayhints.items()
        if path.endswith(":") and path not in ignore_paths and not bool(hint.get("keyorder"))
    ]

    # TODO test second part
    assert missing_keyorders == [], (
        "Missing 'keyorder' in %s. The 'keyorder' should contain at least the key columns."
        % ",".join(missing_keyorders)
    )

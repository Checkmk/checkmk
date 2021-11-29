#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
from typing import Any, Callable, Dict, Generator, List

import cmk.utils.misc
from cmk.utils.check_utils import maincheckify

from cmk.base.api.agent_based.inventory_classes import (
    Attributes,
    InventoryFunction,
    InventoryPlugin,
    InventoryResult,
    TableRow,
)
from cmk.base.api.agent_based.register.inventory_plugins import create_inventory_plugin
from cmk.base.api.agent_based.type_defs import Parameters


class MockStructuredDataNode:
    def __init__(self):
        self.attributes = {}
        self.tables = {}

    @staticmethod
    def _normalize(path: str):
        return tuple(path.strip(":.").split("."))

    def get_dict(self, path: str):
        return self.attributes.setdefault(self._normalize(path), {})

    def get_list(self, path: str):
        return self.tables.setdefault(self._normalize(path), [])


g_inv_tree = MockStructuredDataNode()  # every plugin will get its own!


def inv_tree(path: str) -> Dict:
    return g_inv_tree.get_dict(path)


def inv_tree_list(path: str) -> List:
    return g_inv_tree.get_list(path)


def get_inventory_context() -> Dict[str, Any]:
    return {
        "inv_tree_list": inv_tree_list,
        "inv_tree": inv_tree,
    }


def _create_inventory_function(
    legacy_inventory_function: Callable,
    has_params: bool,
) -> InventoryFunction:
    """Create an API compliant inventory function"""

    def _inventory_generator(*args) -> InventoryResult:
        # mock the inventory/status data trees to later generate API objects
        # base on the info contained in them after running the legacy inventory function
        local_status_data_tree = MockStructuredDataNode()
        local_inventory_tree = MockStructuredDataNode()
        global g_inv_tree
        g_inv_tree = local_inventory_tree

        # Let the legacy plugin fill the newly created trees.
        # Exceptions just raise through
        legacy_inventory_function(
            *args,
            **cmk.utils.misc.make_kwargs_for(
                legacy_inventory_function,
                inventory_tree=local_inventory_tree,
                status_data_tree=local_status_data_tree,
            ),
        )

        # Convert the content of the trees to the new API. Add a hint if this fails:
        try:
            yield from _generate_api_objects(local_status_data_tree, local_inventory_tree)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "Unable to convert legacy results. Please migrate plugin to new API"
            ) from exc

    if has_params:

        def inventory_migration_wrapper(
            params: Parameters,
            section: Any,
        ) -> InventoryResult:
            yield from _inventory_generator(section, params)

    else:

        def inventory_migration_wrapper(  # type: ignore[misc] # different args on purpose!
            section: Any,
        ) -> InventoryResult:
            yield from _inventory_generator(section)

    return inventory_migration_wrapper


def _function_has_params(legacy_function: Callable) -> bool:
    return (
        len(
            set(cmk.utils.misc.getfuncargs(legacy_function))
            - {"status_data_tree", "inventory_tree"}
        )
        > 1
    )


def _generate_api_objects(
    local_status_data_tree: MockStructuredDataNode,
    local_inventory_tree: MockStructuredDataNode,
) -> InventoryResult:

    yield from _generate_attributes(local_status_data_tree, local_inventory_tree)
    yield from _generate_table_rows(local_status_data_tree, local_inventory_tree)


def _generate_attributes(
    local_status_data_tree: MockStructuredDataNode,
    local_inventory_tree: MockStructuredDataNode,
) -> Generator[Attributes, None, None]:

    for path in sorted(
        set(local_status_data_tree.attributes) | set(local_inventory_tree.attributes)
    ):
        status_attributes = {
            str(k): v for k, v in local_status_data_tree.attributes.get(path, {}).items()
        }
        inventory_attributes = {
            str(k): v
            for k, v in local_inventory_tree.attributes.get(path, {}).items()
            if str(k) not in status_attributes
        }
        yield Attributes(
            path=list(path),
            inventory_attributes=inventory_attributes,
            status_attributes=status_attributes,
        )


def _generate_table_rows(
    local_status_data_tree: MockStructuredDataNode,
    local_inventory_tree: MockStructuredDataNode,
) -> Generator[TableRow, None, None]:

    for path in sorted(set(local_status_data_tree.tables) | set(local_inventory_tree.tables)):
        inv_table = local_inventory_tree.tables.get(path, [])
        status_table = local_status_data_tree.tables.get(path, [])

        common_inv_keys = (
            {k for k in inv_table[0] if all(k in row for row in inv_table)} if inv_table else set()
        )
        common_status_keys = (
            {k for k in status_table[0] if all(k in row for row in status_table)}
            if status_table
            else set()
        )

        for row in inv_table:
            keys = (common_inv_keys & common_status_keys) or common_inv_keys
            key_columns = {str(k): v for k, v in row.items() if k in keys}
            # key columns must not be empty. If the following construct is empty, somehting
            # quite weird is going on, and we skip the table rows.
            if key_columns:
                yield TableRow(
                    path=list(path),
                    key_columns=key_columns,
                    inventory_columns={str(k): v for k, v in row.items() if k not in keys},
                )
        for row in status_table:
            keys = (common_inv_keys & common_status_keys) or common_status_keys
            key_columns = {str(k): v for k, v in row.items() if k in keys}
            if key_columns:
                yield TableRow(
                    path=list(path),
                    key_columns=key_columns,
                    status_columns={str(k): v for k, v in row.items() if k not in keys},
                )


def create_inventory_plugin_from_legacy(
    inventory_plugin_name: str,
    inventory_info_dict: Dict[str, Any],
) -> InventoryPlugin:

    if inventory_info_dict.get("depends_on"):
        raise NotImplementedError("cannot auto-migrate plugins with dependencies")

    new_inventory_name = maincheckify(inventory_plugin_name)

    legacy_inventory_function = inventory_info_dict["inv_function"]
    has_parameters = _function_has_params(legacy_inventory_function)

    inventory_function = _create_inventory_function(
        legacy_inventory_function,
        has_parameters,
    )

    return create_inventory_plugin(
        name=new_inventory_name,
        sections=[inventory_plugin_name.split(".", 1)[0]],
        inventory_function=inventory_function,
        inventory_default_parameters={} if has_parameters else None,
        inventory_ruleset_name=inventory_plugin_name if has_parameters else None,
        module=None,
    )

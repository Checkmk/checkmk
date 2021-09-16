#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Background tools required to register a check plugin
"""
import functools
from typing import Any, Callable, Iterable, List, Mapping, Optional

from cmk.utils.type_defs import InventoryPluginName, RuleSetName

from cmk.base.api.agent_based.inventory_classes import (
    Attributes,
    InventoryFunction,
    InventoryPlugin,
    TableRow,
)
from cmk.base.api.agent_based.register.utils import (
    create_subscribed_sections,
    validate_default_parameters,
    validate_function_arguments,
)


def _filter_inventory(
    generator: Callable[..., Iterable],
) -> InventoryFunction:
    """Only let Attributes and TableRow instances through

    This allows for better typing in base code.
    """

    @functools.wraps(generator)
    def filtered_generator(*args, **kwargs):
        for element in generator(*args, **kwargs):
            if not isinstance(element, (Attributes, TableRow)):
                raise TypeError("unexpected type in inventory function: %r" % type(element))
            yield element

    return filtered_generator


def create_inventory_plugin(
    *,
    name: str,
    sections: Optional[List[str]] = None,
    inventory_function: Callable,
    inventory_default_parameters: Optional[Mapping[str, Any]] = None,
    inventory_ruleset_name: Optional[str] = None,
    module: Optional[str] = None,
) -> InventoryPlugin:
    """Return an InventoryPlugin object after validating and converting the arguments one by one

    For a detailed description of the parameters please refer to the exposed function in the
    'register' namespace of the API.
    """
    plugin_name = InventoryPluginName(name)

    subscribed_sections = create_subscribed_sections(sections, plugin_name)

    validate_function_arguments(
        type_label="inventory",
        function=inventory_function,
        has_item=False,
        default_params=inventory_default_parameters,
        sections=subscribed_sections,
    )

    # validate check arguments
    validate_default_parameters(
        "inventory",
        inventory_ruleset_name,
        inventory_default_parameters,
    )

    return InventoryPlugin(
        name=plugin_name,
        sections=subscribed_sections,
        inventory_function=_filter_inventory(inventory_function),
        inventory_default_parameters=inventory_default_parameters or {},
        inventory_ruleset_name=(
            RuleSetName(inventory_ruleset_name) if inventory_ruleset_name else None
        ),
        module=module,
    )

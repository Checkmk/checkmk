#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for check plug-ins"""

from collections.abc import Callable
from typing import NamedTuple

from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.rulesets import RuleSetName

from cmk.checkengine.inventory import InventoryPluginName
from cmk.checkengine.sectionparser import ParsedSectionName

from cmk.agent_based.v1.type_defs import InventoryResult

InventoryFunction = Callable[..., InventoryResult]


class InventoryPlugin(NamedTuple):
    name: InventoryPluginName
    sections: list[ParsedSectionName]
    inventory_function: InventoryFunction
    inventory_default_parameters: ParametersTypeAlias
    inventory_ruleset_name: RuleSetName | None
    full_module: str

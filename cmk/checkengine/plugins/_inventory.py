#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

from cmk.ccc.validatedstr import ValidatedString

from cmk.utils.rulesets import RuleSetName

from cmk.checkengine.sectionparser import (
    ParsedSectionName,
)

from cmk.agent_based.v1 import Attributes, TableRow
from cmk.discover_plugins import PluginLocation


class InventoryPluginName(ValidatedString):
    pass


@dataclass(frozen=True)
class InventoryPlugin:
    name: InventoryPluginName
    sections: Sequence[ParsedSectionName]
    function: Callable[..., Iterable[Attributes | TableRow]]
    ruleset_name: RuleSetName | None
    defaults: Mapping[str, object]
    location: PluginLocation

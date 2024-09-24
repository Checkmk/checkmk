#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for check plugins"""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple

from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.rulesets import RuleSetName

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.sectionparser import ParsedSectionName

from cmk.base.api.agent_based.plugin_classes import RuleSetTypeName

# courtesy to m365_service_health-1.2.1.mkp:
from cmk.agent_based.v1 import (  # pylint: disable=unused-import
    IgnoreResults,
    IgnoreResultsError,
)
from cmk.agent_based.v1.type_defs import CheckResult, DiscoveryResult

CheckFunction = Callable[..., CheckResult]
DiscoveryFunction = Callable[..., DiscoveryResult]


class CheckPlugin(NamedTuple):
    name: CheckPluginName
    sections: list[ParsedSectionName]
    service_name: str
    discovery_function: DiscoveryFunction
    discovery_default_parameters: ParametersTypeAlias | None
    discovery_ruleset_name: RuleSetName | None
    discovery_ruleset_type: RuleSetTypeName
    check_function: CheckFunction
    check_default_parameters: ParametersTypeAlias | None
    check_ruleset_name: RuleSetName | None
    cluster_check_function: CheckFunction | None
    full_module: str | None  # not available for auto migrated plugins.

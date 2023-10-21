#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for check plugins
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Iterable, NamedTuple

from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.rulesets import RuleSetName

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.checkresults import MetricTuple
from cmk.checkengine.sectionparser import ParsedSectionName

from cmk.base.api.agent_based.type_defs import RuleSetTypeName

from cmk.agent_based.v1 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    Result,
)

CheckFunction = Callable[..., CheckResult]
DiscoveryFunction = Callable[..., DiscoveryResult]


def consume_check_results(
    # TODO(ml):  We should limit the type to `CheckResult` but that leads to
    # layering violations.  We could also go with dependency inversion or some
    # other slightly higher abstraction.  The code here is really concrete.
    # Investigate and find a solution later.
    subresults: Iterable[object],
) -> tuple[Sequence[MetricTuple], Sequence[Result]]:
    """Impedance matching between the Check API and the Check Engine."""
    ignore_results: list[IgnoreResults] = []
    results: list[Result] = []
    perfdata: list[MetricTuple] = []
    for subr in subresults:
        if isinstance(subr, IgnoreResults):
            ignore_results.append(subr)
        elif isinstance(subr, Metric):
            perfdata.append((subr.name, subr.value) + subr.levels + subr.boundaries)
        elif isinstance(subr, Result):
            results.append(subr)
        else:
            raise TypeError(subr)

    # Consume *all* check results, and *then* raise, if we encountered
    # an IgnoreResults instance.
    if ignore_results:
        raise IgnoreResultsError(str(ignore_results[-1]))

    return perfdata, results


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

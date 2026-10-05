#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Base classes and registry for automation results.

Provides the global registry that all concrete result modules register into.
The result type itself is cmk.automations.internal.AutomationResult.
"""

from typing import override

from cmk.automations.internal import AutomationID, AutomationResult
from cmk.ccc.plugin_registry import Registry
from cmk.ruleset_matcher.labels import HostLabelValueDict

DiscoveredHostLabelsDict = dict[str, HostLabelValueDict]


class ResultTypeRegistry(Registry[type[AutomationResult]]):
    @override
    def plugin_name(self, instance: type[AutomationResult]) -> AutomationID:
        return instance.automation_call()


result_type_registry = ResultTypeRegistry()

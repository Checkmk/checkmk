#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cmk.utils.hostaddress import HostName
from cmk.utils.rulesets import RuleSetName

from cmk.checkengine.check_table import ConfiguredService
from cmk.checkengine.checkresults import ServiceCheckResult
from cmk.checkengine.sectionparser import ParsedSectionName

__all__ = ["CheckPlugin"]


@dataclass(frozen=True)
class CheckPlugin:
    sections: Sequence[ParsedSectionName]
    function: Callable[[HostName, ConfiguredService], Callable[..., ServiceCheckResult]]
    default_parameters: Mapping[str, object] | None
    ruleset_name: RuleSetName | None

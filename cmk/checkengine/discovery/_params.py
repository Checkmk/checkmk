#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import itertools
from collections.abc import Callable, Mapping, Sequence
from typing import Literal

from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.hostaddress import HostName
from cmk.utils.rulesets import RuleSetName

from cmk.checkengine.parameters import Parameters

from ._filters import RediscoveryParameters

type ConfigGetter = Callable[
    [HostName, RuleSetName, Literal["merged", "all"]],
    Mapping[str, object] | Sequence[Mapping[str, object]],
]


@dataclasses.dataclass(frozen=True)
class DiscoveryCheckParameters:
    commandline_only: bool
    check_interval: int
    severity_new_services: int
    severity_vanished_services: int
    severity_changed_service_labels: int
    severity_changed_service_params: int
    severity_new_host_labels: int
    rediscovery: RediscoveryParameters


def get_plugin_parameters(
    host_name: HostName,
    config_getter: ConfigGetter,
    *,
    default_parameters: ParametersTypeAlias | None,
    ruleset_name: RuleSetName | None,
    ruleset_type: Literal["all", "merged"],
) -> None | Parameters | list[Parameters]:
    if default_parameters is None:
        # This means the function will not accept any params.
        return None
    if ruleset_name is None:
        # This means we have default params, but no rule set.
        # Not very sensical for discovery functions, but not forbidden by the API either.
        return Parameters(default_parameters)

    config = config_getter(host_name, ruleset_name, ruleset_type)
    if isinstance(config, Sequence):
        return [Parameters(d) for d in itertools.chain(config, (default_parameters,))]

    if ruleset_type == "merged":
        return Parameters({**default_parameters, **config})

    # validation should have prevented this
    raise NotImplementedError(f"unknown discovery rule set type {ruleset_type!r}")

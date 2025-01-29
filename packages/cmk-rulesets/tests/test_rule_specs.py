#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import (
    ActiveCheck,
    AgentAccess,
    AgentConfig,
    CheckParameters,
    DiscoveryParameters,
    EnforcedService,
    EvalType,
    HostAndServiceCondition,
    HostCondition,
    InventoryParameters,
    NotificationParameters,
    Service,
    SNMP,
    SpecialAgent,
    Topic,
)


# ignore mypy errors due to `Any` since we care about testing the name validation
@pytest.mark.parametrize(
    ["name"],
    [
        pytest.param("element\x07bc", id="invalid identifier"),
        pytest.param("global", id="reserved identifier"),
    ],
)
@pytest.mark.parametrize(
    ["input_rulespec", "kwargs"],
    [
        pytest.param(
            ActiveCheck,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
            },
            id="ActiveCheck",
        ),
        pytest.param(
            AgentAccess,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
                "eval_type": EvalType.MERGE,
            },
            id="AgentAccess",
        ),
        pytest.param(
            AgentConfig,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
            },
            id="AgentConfig",
        ),
        pytest.param(
            CheckParameters,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
                "condition": HostCondition(),
            },
            id="CheckParameters",
        ),
        pytest.param(
            DiscoveryParameters,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
            },
            id="DiscoveryParameters",
        ),
        pytest.param(
            EnforcedService,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
                "condition": HostCondition(),
            },
            id="EnforcedService",
        ),
        pytest.param(
            InventoryParameters,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
            },
            id="InventoryParameters",
        ),
        pytest.param(
            NotificationParameters,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
            },
            id="NotificationParameters",
        ),
        pytest.param(
            Service,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
                "eval_type": EvalType.MERGE,
                "condition": HostAndServiceCondition(),
            },
            id="Service",
        ),
        pytest.param(
            SNMP,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
                "eval_type": EvalType.MERGE,
            },
            id="SNMP",
        ),
        pytest.param(
            SpecialAgent,
            {
                "title": Title("ABC"),
                "topic": Topic.APPLICATIONS,
                "parameter_form": lambda: Dictionary(elements={}),
            },
            id="SpecialAgent",
        ),
    ],
)
def test_ruleset_name_validation(
    name: str,
    input_rulespec: (
        type[ActiveCheck]
        | type[AgentAccess]
        | type[AgentConfig]
        | type[CheckParameters]
        | type[DiscoveryParameters]
        | type[EnforcedService]
        | type[InventoryParameters]
        | type[NotificationParameters]
        | type[Service]
        | type[SNMP]
        | type[SpecialAgent]
    ),
    kwargs: Mapping[str, Any],
) -> None:
    with pytest.raises(
        ValueError, match=f"'{name}' is not a valid, non-reserved Python identifier"
    ):
        input_rulespec(name=name, **kwargs)

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.aws_v2.constants import AWS_REGIONS
from cmk.plugins.aws_v2.rulesets.aws import configuration_regions_and_tags, configuration_services
from cmk.plugins.aws_v2.server_side_calls.agent_aws import special_agent_aws_v2
from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import AWS_SERVICES
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, MultipleChoice
from cmk.server_side_calls.v1 import HostConfig, Secret


def _parameter_form[T](
    elements: Mapping[str, DictElement[object]], key: str, form_type: type[T]
) -> T:
    if not isinstance(form := elements[key].parameter_form, form_type):
        raise TypeError(form)
    return form


def _values_of(option: str, params: Mapping[str, object]) -> set[str | Secret]:
    (command,) = special_agent_aws_v2(
        {"auth": ("none", None), "piggyback_naming_convention": "ip_region_instance", **params},
        HostConfig(name="testhost"),
    )
    arguments: Sequence[str | Secret] = command.command_arguments
    return {value for name, value in zip(arguments, arguments[1:]) if name == option}


# fmt: off
@pytest.mark.parametrize(
    ("services_key", "option", "global_service"),
    [
        pytest.param("global_services", "--global-service", True, id="global services"),
        pytest.param("regional_services", "--service", False, id="regional services"),
    ],
)
# fmt: on
def test_rule_offers_exactly_the_services_of_the_agent(
    services_key: str, option: str, global_service: bool
) -> None:
    form = _parameter_form(configuration_services(), services_key, Dictionary)
    every_service: dict[str, object] = {
        name: ("all", {}) for name in (*form.elements, *form.ignored_elements)
    }

    passed_services = _values_of(option, {services_key: every_service})

    assert passed_services == {s.key for s in AWS_SERVICES if s.global_service is global_service}


def test_rule_offers_every_region_of_the_agent_by_its_aws_id() -> None:
    form = _parameter_form(configuration_regions_and_tags(), "regions", MultipleChoice)

    passed_regions = _values_of("--region", {"regions": [e.name for e in form.elements]})

    assert passed_regions == {region_id for region_id, _region_name in AWS_REGIONS}


def test_saved_ultimate_only_services_are_kept_without_the_extended_package() -> None:
    # This test target does not contain the aws_v2_extended package.
    global_form = _parameter_form(configuration_services(), "global_services", Dictionary)
    regional_form = _parameter_form(configuration_services(), "regional_services", Dictionary)

    assert set(global_form.ignored_elements) == {"route53", "cloudfront"}
    assert set(regional_form.ignored_elements) == {"aws_lambda", "sns", "ecs", "elasticache"}

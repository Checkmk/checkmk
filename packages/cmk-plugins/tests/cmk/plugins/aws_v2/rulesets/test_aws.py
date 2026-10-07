#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.plugins.aws_v2.constants import AWS_REGIONS
from cmk.plugins.aws_v2.rulesets.aws import configuration_regions_and_tags
from cmk.plugins.aws_v2.server_side_calls.agent_aws import special_agent_aws_v2
from cmk.rulesets.v1.form_specs import DictElement, MultipleChoice
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


def test_rule_offers_every_region_of_the_agent_by_its_aws_id() -> None:
    form = _parameter_form(configuration_regions_and_tags(), "regions", MultipleChoice)

    passed_regions = _values_of("--region", {"regions": [e.name for e in form.elements]})

    assert passed_regions == {region_id for region_id, _region_name in AWS_REGIONS}

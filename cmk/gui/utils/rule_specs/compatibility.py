#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import cast

from cmk.gui.form_specs.unstable.legacy_converter.transform import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.rulesets.v1 import rule_specs
from cmk.rulesets.v1.form_specs import Dictionary

from .types import RuleSpec


def make_rule_spec_backwards_compatible(to_convert: RuleSpec) -> RuleSpec:
    if isinstance(to_convert, rule_specs.AgentConfig):
        return _make_v1_agent_config_backwards_compatible(to_convert)
    return to_convert


def add_agent_config_match_type_key(value: object) -> object:
    if isinstance(value, dict):
        value["cmk-match-type"] = "dict"
        return value

    raise TypeError(value)


def remove_agent_config_match_type_key(value: object) -> object:
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if k != "cmk-match-type"}

    raise TypeError(value)


def _make_v1_agent_config_backwards_compatible(
    to_convert: rule_specs.AgentConfig,
) -> rule_specs.AgentConfig:
    parameter_form = lambda: cast(
        Dictionary,
        TransformDataForLegacyFormatOrRecomposeFunction(
            wrapped_form_spec=to_convert.parameter_form,
            from_disk=remove_agent_config_match_type_key,
            to_disk=add_agent_config_match_type_key,
        ),
    )

    return rule_specs.AgentConfig(
        title=to_convert.title,
        topic=to_convert.topic,
        parameter_form=parameter_form,
        name=to_convert.name,
        is_deprecated=to_convert.is_deprecated,
        help_text=to_convert.help_text,
    )

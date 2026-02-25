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
    """
    This function is a relict from when we had to do some back and forth
    transformation on AgentConfig rule specs. This is not necessary anymore.
    BUT
    Removing this function entirely changes the caching behavior of the FormSpec,
    as can be seen by some _potentially_ breaking tests (depending on test order).
    CMK-32061
    """
    if not isinstance(to_convert, rule_specs.AgentConfig):
        return to_convert

    return rule_specs.AgentConfig(
        title=to_convert.title,
        topic=to_convert.topic,
        parameter_form=lambda: cast(
            Dictionary,
            TransformDataForLegacyFormatOrRecomposeFunction(
                wrapped_form_spec=to_convert.parameter_form,
                from_disk=lambda x: x,
                to_disk=lambda x: x,
            ),
        ),
        name=to_convert.name,
        is_deprecated=to_convert.is_deprecated,
        help_text=to_convert.help_text,
    )

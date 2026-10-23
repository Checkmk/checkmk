#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.plugins.generic_agent_options.rulesets._topic import TOPIC_LINUX_UNIX_AGENT_OPTIONS
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, String
from cmk.rulesets.v1.rule_specs import AgentConfig

# The keys were renamed to tell rules stored before the migration to the rulesets v1 API
# ("first matching rule wins") from rules stored afterwards (matching rules are merged).
# Both elements are required, so a rule stored by the new form always carries both keys.
_NEW_KEYS = ("distribution_tag", "dist_tag")


def migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    if any(key in value for key in _NEW_KEYS):
        return value
    # Old rule (this includes the empty dict, which the new form never stores): make all
    # parameters explicit so that merging with other rules does not change the outcome.
    # An empty string means "not set".
    return {
        "distribution_tag": value.get("distribution", ""),
        "dist_tag": value.get("disttag", ""),
    }


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "The Linux RPM packages built by the Agent Bakery are packaged independently "
            "of any Linux distribution. Hence, the <tt>DISTRIBUTION</tt> and <tt>DISTTAG</tt> "
            "tags are left empty within the RPM spec file. "
            "Here, you can manually specify these tags."
        ),
        migrate=migrate,
        # Consumed by the RPM package builder (non-free cmk-bakery), not by a bakelet.
        elements={
            "distribution_tag": DictElement(
                required=True,
                parameter_form=String(title=Title("DISTRIBUTION")),
            ),
            "dist_tag": DictElement(
                required=True,
                parameter_form=String(title=Title("DISTTAG")),
            ),
        },
    )


rule_spec_rpm_tags = AgentConfig(
    title=Title("Specify RPM package tags (Linux)"),
    name="rpm_tags",
    topic=TOPIC_LINUX_UNIX_AGENT_OPTIONS,
    parameter_form=_form_spec,
)

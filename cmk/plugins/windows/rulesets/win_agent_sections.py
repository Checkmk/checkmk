#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, MultipleChoice
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic

from .windows_sections import migrate_sections, section_choices, WINDOWS_SECTIONS


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This option allows to select specific sections of the Checkmk agent. "
            "All of the sections checked below will be executed. "
            "Sections that are not selected here will be skipped. "
            "Skipping sections reduces CPU load on the monitored host and the amount "
            "of transferred data. However, it may result in the absence of the associated "
            "Checkmk service or services. "
            "The most CPU performance is needed by the Eventlog monitoring and the "
            "performance counters. "
        ),
        migrate=migrate_sections,
        elements={
            "sections": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Enabled sections"),
                    elements=section_choices(),
                    prefill=DefaultValue(
                        [s.name for s in WINDOWS_SECTIONS if s.enabled_by_default]
                    ),
                ),
            ),
        },
    )


rule_spec_win_agent_sections = AgentConfig(
    title=Title("Enabled sections (Windows agent)"),
    name="win_agent_sections",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)

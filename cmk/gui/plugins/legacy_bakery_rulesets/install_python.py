#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _form_spec() -> Dictionary:
    return Dictionary(
        elements={
            # Consumed by the Windows agent package builder, not by this bakelet.
            "installation": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Installation"),
                    help_text=Help(
                        "This rule set allows to add embedded Python "
                        "to the Windows agent installation."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="auto",
                            title=Title(
                                "Install Python automatically when configured plug-ins need it"
                            ),
                        ),
                        SingleChoiceElement(
                            name="install",
                            title=Title("Always install Python with agent"),
                        ),
                        SingleChoiceElement(
                            name="no_install",
                            title=Title("Never install Python with the agent"),
                        ),
                    ],
                    prefill=DefaultValue("auto"),
                ),
            ),
            "usage": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Usage"),
                    help_text=Help(
                        "This rule set allows to choose which Python interpreter is used "
                        "to run Python scripts."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="auto",
                            title=Title("Use Checkmk Python, if it has been installed"),
                        ),
                        SingleChoiceElement(
                            name="system",
                            title=Title("Do not use Checkmk Python, even if it has been installed"),
                        ),
                    ],
                    prefill=DefaultValue("auto"),
                ),
            ),
        },
    )


rule_spec_install_python = AgentConfig(
    title=Title("Install Python runtime environment"),
    name="install_python",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import form_specs, rule_specs, Title


def _parameter_form_prism_vm_tools():
    return form_specs.Dictionary(
        elements={
            "tools_install": form_specs.DictElement(
                parameter_form=form_specs.SingleChoice(
                    title=Title("Tools install state"),
                    elements=[
                        form_specs.SingleChoiceElement(
                            name="installed",
                            title=Title("installed"),
                        ),
                        form_specs.SingleChoiceElement(
                            name="not_installed",
                            title=Title("not installed"),
                        ),
                        form_specs.SingleChoiceElement(
                            name="ignored",
                            title=Title("ignored"),
                        ),
                    ],
                    prefill=form_specs.DefaultValue("installed"),
                )
            ),
            "tools_enabled": form_specs.DictElement(
                parameter_form=form_specs.SingleChoice(
                    title=Title("VMTools activation state"),
                    elements=[
                        form_specs.SingleChoiceElement(
                            name="enabled",
                            title=Title("enabled"),
                        ),
                        form_specs.SingleChoiceElement(
                            name="disabled",
                            title=Title("not disabled"),
                        ),
                        form_specs.SingleChoiceElement(
                            name="ignored",
                            title=Title("ignored"),
                        ),
                    ],
                    prefill=form_specs.DefaultValue("enabled"),
                )
            ),
        },
        title=Title("Wanted VM State for defined Nutanix VMs"),
    )


rule_spec_prism_vm_tools = rule_specs.CheckParameters(
    name="prism_vm_tools",
    topic=rule_specs.Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_prism_vm_tools,
    title=Title("Nutanix Prism VM Tools"),
    condition=rule_specs.HostCondition(),
)

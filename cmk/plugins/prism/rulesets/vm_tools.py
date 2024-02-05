#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import cmk.rulesets.v1.form_specs.basic
from cmk.rulesets.v1 import form_specs, Localizable, rule_specs


def _parameter_form_prism_vm_tools():
    return form_specs.composed.Dictionary(
        elements={
            "tools_install": form_specs.composed.DictElement(
                parameter_form=cmk.rulesets.v1.form_specs.basic.SingleChoice(
                    title=Localizable("Tools install state"),
                    elements=[
                        cmk.rulesets.v1.form_specs.basic.SingleChoiceElement(
                            name="installed",
                            title=Localizable("installed"),
                        ),
                        cmk.rulesets.v1.form_specs.basic.SingleChoiceElement(
                            name="not_installed",
                            title=Localizable("not installed"),
                        ),
                        cmk.rulesets.v1.form_specs.basic.SingleChoiceElement(
                            name="ignored",
                            title=Localizable("ignored"),
                        ),
                    ],
                    prefill=form_specs.DefaultValue("installed"),
                )
            ),
            "tools_enabled": form_specs.composed.DictElement(
                parameter_form=cmk.rulesets.v1.form_specs.basic.SingleChoice(
                    title=Localizable("VMTools activation state"),
                    elements=[
                        cmk.rulesets.v1.form_specs.basic.SingleChoiceElement(
                            name="enabled",
                            title=Localizable("enabled"),
                        ),
                        cmk.rulesets.v1.form_specs.basic.SingleChoiceElement(
                            name="disabled",
                            title=Localizable("not disabled"),
                        ),
                        cmk.rulesets.v1.form_specs.basic.SingleChoiceElement(
                            name="ignored",
                            title=Localizable("ignored"),
                        ),
                    ],
                    prefill=form_specs.DefaultValue("enabled"),
                )
            ),
        },
        title=Localizable("Wanted VM State for defined Nutanix VMs"),
    )


rule_spec_prism_vm_tools = rule_specs.CheckParameters(
    name="prism_vm_tools",
    topic=rule_specs.Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_prism_vm_tools,
    title=Localizable("Nutanix Prism VM Tools"),
    condition=rule_specs.HostCondition(),
)

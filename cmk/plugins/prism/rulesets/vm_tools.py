#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import form_specs, Localizable, rule_specs


def _parameter_form_prism_vm_tools():
    return form_specs.Dictionary(
        elements={
            "tools_install": form_specs.DictElement(
                parameter_form=form_specs.DropdownChoice(
                    title=Localizable("Tools install state"),
                    elements=[
                        form_specs.DropdownChoiceElement(
                            name="installed",
                            title=Localizable("installed"),
                        ),
                        form_specs.DropdownChoiceElement(
                            name="not_installed",
                            title=Localizable("not installed"),
                        ),
                        form_specs.DropdownChoiceElement(
                            name="ignored",
                            title=Localizable("ignored"),
                        ),
                    ],
                    prefill_selection="installed",
                )
            ),
            "tools_enabled": form_specs.DictElement(
                parameter_form=form_specs.DropdownChoice(
                    title=Localizable("VMTools activation state"),
                    elements=[
                        form_specs.DropdownChoiceElement(
                            name="enabled",
                            title=Localizable("enabled"),
                        ),
                        form_specs.DropdownChoiceElement(
                            name="disabled",
                            title=Localizable("not disabled"),
                        ),
                        form_specs.DropdownChoiceElement(
                            name="ignored",
                            title=Localizable("ignored"),
                        ),
                    ],
                    prefill_selection="enabled",
                )
            ),
        },
        title=Localizable("Wanted VM State for defined Nutanix VMs"),
    )


rule_spec_prism_vm_tools = rule_specs.CheckParameterWithoutItem(
    name="prism_vm_tools",
    topic=rule_specs.Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_prism_vm_tools,
    title=Localizable("Nutanix Prism VM Tools"),
)

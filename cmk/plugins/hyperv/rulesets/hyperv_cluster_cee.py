#!/usr/bin/python
'''Deployment ruleset for Hyper-V Cluster plugins.'''
# -*- encoding: utf-8; py-indent-offst: 4 -*-

# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
# License: GNU General Public License v2

from cmk.rulesets.v1 import Title, Label, Help
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DictElement,
    Dictionary,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _valuespec_agent_config_hyperv_cluster():
    return Dictionary(
        title=Title("Hyper-V Cluster Plugins"),
        help_text=Help(
            "This plugin checks the status of Hyper-V Cluster."
        ),
        elements={
            "deploy": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Deploy plugin for Hyper-V Cluster plugin"),
                ),
                required=True,
            ),
        },
    )


rule_spec_agent_config_hyperv_cluster = AgentConfig(
    title=Title("Hyper-V Cluster Plugins"),
    topic=Topic.WINDOWS,
    name="hyperv_cluster",
    parameter_form=_valuespec_agent_config_hyperv_cluster,
)

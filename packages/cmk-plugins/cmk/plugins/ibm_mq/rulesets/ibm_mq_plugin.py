#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.ibm_mq.rulesets.lib import version_form
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_ibm_mq_plugin() -> Dictionary:
    return Dictionary(
        elements={
            "version": DictElement(parameter_form=version_form()),
        },
    )


rule_spec_ibm_mq_plugin = CheckParameters(
    name="ibm_mq_plugin",
    title=Title("IBM MQ plug-in"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_ibm_mq_plugin,
    condition=HostCondition(),
)

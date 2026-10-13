#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import BooleanChoice, DefaultValue, DictElement, Dictionary
from cmk.rulesets.v1.rule_specs import DiscoveryParameters, Topic


def _parameter_form_discovery_veeam_cdp_jobs() -> Dictionary:
    return Dictionary(
        elements={
            "discover_disabled": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Disabled CDP jobs"),
                    label=Label("Discover disabled CDP jobs"),
                    help_text=Help(
                        "By default, a service is also created for a CDP job that is disabled "
                        "in Veeam; it is always OK. Disable this option to create no services "
                        "for disabled CDP jobs."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
        },
    )


rule_spec_discovery_veeam_cdp_jobs = DiscoveryParameters(
    name="discovery_veeam_cdp_jobs",
    title=Title("Veeam: CDP job discovery"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_discovery_veeam_cdp_jobs,
)

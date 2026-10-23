#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import BooleanChoice, DefaultValue, DictElement, Dictionary
from cmk.rulesets.v1.rule_specs import DiscoveryParameters, Topic


def _parameter_form_discovery_veeam_backup_jobs() -> Dictionary:
    return Dictionary(
        elements={
            "discover_disabled": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Disabled backup jobs"),
                    label=Label("Discover disabled backup jobs"),
                    help_text=Help(
                        "By default, a service is also created for a backup job that is disabled "
                        "in Veeam; it is OK by default. Disable this option to create no services "
                        "for disabled backup jobs."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
        },
    )


rule_spec_discovery_veeam_backup_jobs = DiscoveryParameters(
    name="discovery_veeam_backup_jobs",
    title=Title("Veeam: Backup job discovery"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_discovery_veeam_backup_jobs,
)

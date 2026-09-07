#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _migrate_site(item: object) -> Mapping[str, object]:
    if isinstance(item, dict):
        return item
    seq = list(item) if isinstance(item, (list, tuple)) else [item]
    return {
        "site_name": seq[0],
        "tags": seq[1] if len(seq) > 1 else [],
        "service_check_commands": seq[2] if len(seq) > 2 else [],
    }


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if isinstance(value, dict):
        # Old rule ("first matching rule wins"): make all parameters explicit so that merging
        # with other rules does not change the outcome. Empty lists mean "nothing configured".
        sites = value.get("sites", [])
        return {
            "deployment": ("sync", None),
            "tags": value.get("tags", []),
            "service_check_commands": value.get("service_check_commands", []),
            "sites": [_migrate_site(s) for s in sites] if isinstance(sites, (list, tuple)) else [],
        }
    raise ValueError(f"Unexpected value: {value!r}")


def _valuespec_agent_config_mk_site_object_counts() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This will deploy and configure the Checkmk agent plug-in <tt>mk_site_object_counts</tt>. "
            "The plug-in runs below the specified user's environment. Furthermore you have to "
            "determine host tags or service check commands."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the plug-in and run it synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="cached",
                            title=Title("Deploy the plug-in and run it asynchronously"),
                            parameter_form=TimeSpan(
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "tags": DictElement(
                parameter_form=List(
                    element_template=String(),
                    title=Title("Tags"),
                ),
            ),
            "service_check_commands": DictElement(
                parameter_form=List(
                    element_template=String(),
                    title=Title("Service check commands"),
                ),
            ),
            "sites": DictElement(
                parameter_form=List(
                    element_template=Dictionary(
                        title=Title("Site configuration"),
                        elements={
                            "site_name": DictElement(
                                required=True,
                                parameter_form=String(title=Title("Site name")),
                            ),
                            "tags": DictElement(
                                parameter_form=List(
                                    element_template=String(),
                                    title=Title("Tags"),
                                ),
                            ),
                            "service_check_commands": DictElement(
                                parameter_form=List(
                                    element_template=String(),
                                    title=Title("Service check commands"),
                                ),
                            ),
                        },
                    ),
                    title=Title("Sites"),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_mk_site_object_counts = AgentConfig(
    title=Title("Checkmk site objects"),
    name="mk_site_object_counts",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_agent_config_mk_site_object_counts,
)

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.gcp.lib import constants
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        migrate=_migrate,
        elements={
            "regions": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Regions to monitor"),
                    elements=[
                        MultipleChoiceElement(
                            name=_region_identifier_to_python_identifier(k),
                            title=Title("%s | %s") % (k, v),
                        )
                        for k, v in sorted(constants.RegionMap.items())
                    ],
                ),
            )
        },
    )


rule_spec_special_agent_gcp_status = SpecialAgent(
    name="gcp_status",
    title=Title("Google Cloud Platform (GCP) Status"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form,
)


def _region_identifier_to_python_identifier(region_id: str) -> str:
    return region_id.replace("-", "_")


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)
    return {
        "regions": [
            _region_identifier_to_python_identifier(region_id) for region_id in value["regions"]
        ]
    }

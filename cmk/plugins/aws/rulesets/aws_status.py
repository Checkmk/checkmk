#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.plugins.aws.lib import aws_region_to_monitor
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _convert_regions(values: object) -> list[str]:
    assert isinstance(values, list)
    return [region.replace("-", "_") for region in values]


def _pre_24_to_formspec_migration(values: object) -> dict[str, object]:
    assert isinstance(values, dict)

    # Proxy migrate regions -> regions_to_monitor to indicate migration has been applied
    if "regions_to_monitor" in values:
        return values

    values["regions"] = _convert_regions(values["regions"])

    values["regions_to_monitor"] = values.pop("regions")
    return values


def _formspec_aws():
    return Dictionary(
        title=Title("Amazon Web Services (AWS) Status"),
        migrate=_pre_24_to_formspec_migration,
        elements={
            "regions_to_monitor": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Regions to monitor"),
                    elements=[
                        MultipleChoiceElement(
                            name=name.replace("-", "_"),
                            title=Title(  # pylint: disable=localization-of-non-literal-string
                                title
                            ),
                        )
                        for name, title in aws_region_to_monitor()
                    ],
                ),
                required=True,
            ),
        },
    )


rule_spec_aws_status = SpecialAgent(
    name="aws_status",
    title=Title("Amazon Web Services (AWS) Status"),
    topic=Topic.CLOUD,
    parameter_form=_formspec_aws,
)

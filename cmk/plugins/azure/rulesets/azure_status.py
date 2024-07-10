#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.utils.azure_constants import AZURE_REGIONS

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _regions_to_monitor() -> Sequence[MultipleChoiceElement]:
    def key(regionid_display: tuple[str, str]) -> str:
        return regionid_display[1]

    def is_gov(regionid_display: tuple[str, str]) -> bool:
        return "DoD" in regionid_display[1] or "Gov" in regionid_display[1]

    regions_by_display_order = [
        *sorted((r for r in AZURE_REGIONS.items() if not is_gov(r)), key=key),
        *sorted((r for r in AZURE_REGIONS.items() if is_gov(r)), key=key),
    ]
    return [
        MultipleChoiceElement(
            name=id_,
            title=Title(f"{region} ({id_})"),  # pylint: disable=localization-of-non-literal-string
        )
        for id_, region in regions_by_display_order
    ]


def _formspec() -> Dictionary:
    return Dictionary(
        elements={
            "regions": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Regions to monitor"),
                    elements=_regions_to_monitor(),
                ),
                required=True,
            )
        },
    )


rule_spec_azure_status = SpecialAgent(
    name="azure_status",
    title=Title("Microsoft Azure Status"),
    topic=Topic.CLOUD,
    parameter_form=_formspec,
)

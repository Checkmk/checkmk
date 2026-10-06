#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    Percentage,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {"levels": ("crit_on_all", None)}
    levels = value.get("levels")
    if not isinstance(levels, tuple):
        return value
    kind, payload = levels
    if kind in ("absolute", "percentage"):
        if isinstance(payload, dict):
            return {"levels": (kind, payload)}
        warn, crit = payload
        # The legacy valuespec could store integer percentages (e.g. its default of 0).
        convert = int if kind == "absolute" else float
        return {"levels": (kind, {"warn": convert(warn), "crit": convert(crit)})}
    # "crit_on_all" and "always_ok" carry no payload (the latter was stored as False).
    return {"levels": (kind, None)}


def _levels_pair(warn: Integer | Percentage, crit: Integer | Percentage) -> Dictionary:
    return Dictionary(
        elements={
            "warn": DictElement(required=True, parameter_form=warn),
            "crit": DictElement(required=True, parameter_form=crit),
        },
    )


def _parameter_form_ibm_svc_license() -> Dictionary:
    return Dictionary(
        migrate=_migrate,
        elements={
            "levels": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Levels for number of licenses"),
                    prefill=DefaultValue("crit_on_all"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="absolute",
                            title=Title("Absolute levels for unused licenses"),
                            parameter_form=_levels_pair(
                                Integer(
                                    title=Title("Warning below"),
                                    unit_symbol="unused licenses",
                                    prefill=DefaultValue(5),
                                ),
                                Integer(
                                    title=Title("Critical below"),
                                    unit_symbol="unused licenses",
                                    prefill=DefaultValue(0),
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="percentage",
                            title=Title("Percentual levels for unused licenses"),
                            parameter_form=_levels_pair(
                                Percentage(
                                    title=Title("Warning below"), prefill=DefaultValue(10.0)
                                ),
                                Percentage(
                                    title=Title("Critical below"), prefill=DefaultValue(0.0)
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="crit_on_all",
                            title=Title("Go critical if all licenses are used"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="always_ok",
                            title=Title("Always be OK"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_ibm_svc_license = CheckParameters(
    name="ibmsvc_licenses",
    title=Title("IBM SVC licenses"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_ibm_svc_license,
    condition=HostAndItemCondition(item_title=Title("ID of the license, e.g. virtualization")),
)

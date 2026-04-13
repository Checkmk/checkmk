#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.watolib import timeperiods
from cmk.rulesets.internal.form_specs import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import FormSpec, TimePeriod


def recompose(form_spec: FormSpec[Any]) -> SingleChoiceExtended[Any]:
    if not isinstance(form_spec, TimePeriod):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a TimePeriod form spec, got {type(form_spec)}"
        )

    return SingleChoiceExtended(
        # FormSpec:
        title=form_spec.title,
        help_text=form_spec.help_text,
        migrate=form_spec.migrate,
        custom_validate=form_spec.custom_validate,
        # SingleChoice
        elements=[
            SingleChoiceElementExtended(
                name=timePeriodName,
                title=Title(  # astrein: disable=localization-checker
                    f"{timePeriodName} - {timePeriodSpec['alias']}"
                ),
            )
            for timePeriodName, timePeriodSpec in timeperiods.load_timeperiods().items()
        ],
    )

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Literal

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs.private import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import FormSpec, HostState


def recompose(form_spec: FormSpec[Any]) -> FormSpec[Any]:
    if not isinstance(form_spec, HostState):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a HostState form spec, got {type(form_spec)}"
        )

    return SingleChoiceExtended[Literal[0, 1, 2]](
        # FormSpec:
        title=form_spec.title,
        help_text=form_spec.help_text,
        migrate=form_spec.migrate,
        custom_validate=form_spec.custom_validate,
        # SingleChoice
        elements=[
            SingleChoiceElementExtended(
                name=HostState.UP,
                title=Title("UP"),
            ),
            SingleChoiceElementExtended(
                name=HostState.DOWN,
                title=Title("DOWN"),
            ),
            SingleChoiceElementExtended(
                name=HostState.UNREACH,
                title=Title("UNREACHABLE"),
            ),
        ],
        prefill=form_spec.prefill,
    )

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

from cmk.utils.quick_setup.definitions import ParsedFormData, QuickSetupStage, StageId
from cmk.utils.quick_setup.widgets import FormSpecId, FormSpecRecap, FormSpecWrapper

from cmk.gui.quick_setup.to_frontend import build_expected_formspec_map, recaps_form_spec

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, FieldSize, String, validators


def test_form_spec_recap() -> None:
    setup_stages = [
        QuickSetupStage(
            stage_id=StageId(1),
            title="stage1",
            configure_components=[
                FormSpecWrapper(
                    id=FormSpecId("wrapper"),
                    form_spec=Dictionary(
                        elements={
                            "test_dict_element": DictElement(
                                parameter_form=String(
                                    title=Title("test title"),
                                    field_size=FieldSize.MEDIUM,
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                                required=True,
                            )
                        }
                    ),
                ),
            ],
            validators=[],
            recap=[],
            button_txt="Next",
        ),
    ]

    form_data: Sequence[ParsedFormData] = [
        {FormSpecId("wrapper"): {"test_dict_element": "I am a test string"}}
    ]
    recap = list(recaps_form_spec(form_data, build_expected_formspec_map(setup_stages)))

    assert len(recap) == 1
    assert isinstance(recap[0], FormSpecRecap)
    assert recap[0].form_spec.data == form_data[0][FormSpecId("wrapper")]  # type: ignore[attr-defined]

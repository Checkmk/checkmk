#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

from tests.unit.cmk.gui.quick_setup.factories import QuickSetupFactory, QuickSetupStageFactory

from cmk.gui.quick_setup.to_frontend import (
    build_quick_setup_formspec_map,
    recaps_form_spec,
    retrieve_next_stage,
)
from cmk.gui.quick_setup.v0_unstable.definitions import IncomingStage
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupStage
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData, RawFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, FormSpecRecap, FormSpecWrapper

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, FieldSize, String, validators


def test_form_spec_recap() -> None:
    setup_stages = [
        QuickSetupStage(
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
            custom_validators=[],
            recap=[],
            button_label="Next",
        ),
    ]

    form_data: Sequence[ParsedFormData] = [
        {FormSpecId("wrapper"): {"test_dict_element": "I am a test string"}}
    ]
    recap = list(recaps_form_spec(form_data, build_quick_setup_formspec_map(setup_stages)))

    assert len(recap) == 1
    assert isinstance(recap[0], FormSpecRecap)
    assert recap[0].form_spec.data == form_data[0][FormSpecId("wrapper")]  # type: ignore[attr-defined]


def test_retrieve_next_following_last_stage() -> None:
    quick_setup = QuickSetupFactory.build(stages=[QuickSetupStageFactory.build()])
    incoming_stages = [IncomingStage(form_data=RawFormData({}))]
    stage = retrieve_next_stage(quick_setup=quick_setup, incoming_stages=incoming_stages)
    assert stage.next_stage_structure is None

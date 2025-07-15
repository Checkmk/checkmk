#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from tests.unit.cmk.gui.quick_setup.factories import QuickSetupFactory

from cmk.gui.quick_setup.handlers.stage import recap_stage
from cmk.gui.quick_setup.handlers.utils import InfoLogger
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.predefined import build_formspec_map_from_stages
from cmk.gui.quick_setup.v0_unstable.predefined._recaps import recaps_form_spec
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupStage, QuickSetupStageAction
from cmk.gui.quick_setup.v0_unstable.type_defs import ActionId, RawFormData, StageIndex
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, FormSpecRecap, FormSpecWrapper

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, FieldSize, String, validators


def test_form_spec_recap() -> None:
    setup_stages = [
        lambda: QuickSetupStage(
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
            actions=[
                QuickSetupStageAction(
                    id=ActionId("action"),
                    custom_validators=[],
                    recap=[recaps_form_spec],
                    next_button_label="Next",
                )
            ],
        ),
    ]
    quick_setup = QuickSetupFactory.build(stages=setup_stages)
    quick_setup_registry.register(quick_setup)
    stage_index = StageIndex(0)

    built_stages = [stage() for stage in quick_setup.stages[: stage_index + 1]]
    form_spec_map = build_formspec_map_from_stages(built_stages)

    stage_recap = recap_stage(
        quick_setup_id=quick_setup.id,
        stage_index=stage_index,
        stages=built_stages,
        stage_action_id=ActionId("action"),
        stages_raw_formspecs=[
            RawFormData({FormSpecId("wrapper"): {"test_dict_element": "I am a test string"}})
        ],
        quick_setup_formspec_map=form_spec_map,
        site_configs={},
        progress_logger=InfoLogger(),
        debug=False,
    )

    assert len(stage_recap) == 1
    assert isinstance(stage_recap[0], FormSpecRecap)
    assert stage_recap[0].form_spec.data == {  # type: ignore[attr-defined]
        "test_dict_element": "I am a test string"
    }

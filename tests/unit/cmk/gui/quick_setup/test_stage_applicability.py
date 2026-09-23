#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.quick_setup.handlers.utils import stage_applicability_and_form_data
from cmk.gui.quick_setup.v0_unstable.predefined import build_formspec_map_from_stages
from cmk.gui.quick_setup.v0_unstable.setups import (
    applicable_if,
    CallableStageApplicability,
    QuickSetupStage,
    QuickSetupStageAction,
    StageFactory,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import ActionId, ParsedFormData, RawFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, FormSpecWrapper
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, String


def _stage(
    form_spec_id: str,
    condition: CallableStageApplicability | None = None,
    *,
    elements: Sequence[str] = ("value",),
    second_form_spec_id: str | None = None,
) -> StageFactory:
    """A stage factory, with the condition declared the way a plug-in declares it."""
    form_spec_ids = [form_spec_id] + ([second_form_spec_id] if second_form_spec_id else [])
    factory: StageFactory = lambda: QuickSetupStage(
        title=form_spec_id,
        configure_components=[
            FormSpecWrapper(
                id=FormSpecId(wrapper_id),
                form_spec=Dictionary(
                    elements={
                        element: DictElement(parameter_form=String(title=Title("element")))
                        for element in elements
                    },
                ),
            )
            for wrapper_id in form_spec_ids
        ],
        actions=[QuickSetupStageAction(id=ActionId("action"), custom_validators=[], recap=[])],
    )
    return applicable_if(condition)(factory) if condition is not None else factory


def _value_is(form_spec_id: str, expected: str) -> CallableStageApplicability:
    def condition(form_data: ParsedFormData) -> bool:
        stage_data = form_data.get(FormSpecId(form_spec_id))
        return isinstance(stage_data, dict) and stage_data.get("value") == expected

    return condition


def _raises(_form_data: ParsedFormData) -> bool:
    raise KeyError("the condition of a badly written plug-in")


@pytest.mark.parametrize(
    "condition, raw_form_data, expected",
    [
        pytest.param(
            _value_is("mode", "pull"),
            [RawFormData({FormSpecId("mode"): {"value": "pull"}})],
            [True, True],
            id="condition is met",
        ),
        pytest.param(
            _value_is("mode", "pull"),
            [RawFormData({FormSpecId("mode"): {"value": "push"}})],
            [True, False],
            id="condition is not met",
        ),
        pytest.param(
            _value_is("mode", "pull"),
            [],
            [True, False],
            id="no form data submitted yet",
        ),
        pytest.param(
            _value_is("mode", "pull"),
            [RawFormData({FormSpecId("mode"): {"value": 5}})],
            [True, False],
            id="invalid form data is not readable",
        ),
        pytest.param(
            _value_is("mode", "pull"),
            [
                RawFormData(
                    {FormSpecId("mode"): {"value": "pull"}, FormSpecId("nope"): {"value": "x"}}
                )
            ],
            [True, True],
            id="unknown form spec id is skipped",
        ),
        pytest.param(
            _raises,
            [RawFormData({FormSpecId("mode"): {"value": "pull"}})],
            [True, False],
            id="condition that raises hides its stage",
        ),
    ],
)
def test_stage_applicability(
    condition: CallableStageApplicability,
    raw_form_data: Sequence[RawFormData],
    expected: list[bool],
) -> None:
    stages = [_stage("mode"), _stage("pull", condition)]

    applicability, _visible_form_data = stage_applicability_and_form_data(
        stages, raw_form_data, build_formspec_map_from_stages([stage() for stage in stages])
    )

    assert applicability == expected


@pytest.mark.parametrize(
    "raw_form_data, expected",
    [
        pytest.param(
            [
                RawFormData({FormSpecId("mode"): {"value": "pull"}}),
                RawFormData({FormSpecId("pull"): {"value": "custom"}}),
                RawFormData({FormSpecId("tls"): {"value": "ca"}}),
            ],
            [True, True, True],
            id="both conditions are met",
        ),
        pytest.param(
            # The condition of the third stage does not mention the mode. It is hidden because
            # the data of the hidden second stage never reaches it.
            [
                RawFormData({FormSpecId("mode"): {"value": "push"}}),
                RawFormData({FormSpecId("pull"): {"value": "custom"}}),
                RawFormData({FormSpecId("tls"): {"value": "ca"}}),
            ],
            [True, False, False],
            id="a hidden stage hides the stage that reads its data",
        ),
    ],
)
def test_cascading_conditions(raw_form_data: Sequence[RawFormData], expected: list[bool]) -> None:
    stages = [
        _stage("mode"),
        _stage("pull", _value_is("mode", "pull")),
        _stage("tls", _value_is("pull", "custom")),
    ]

    applicability, _visible_form_data = stage_applicability_and_form_data(
        stages, raw_form_data, build_formspec_map_from_stages([stage() for stage in stages])
    )

    assert applicability == expected


@pytest.mark.parametrize(
    "raw_form_data, expected",
    [
        pytest.param(
            [
                RawFormData({FormSpecId("mode"): {"value": "pull"}}),
                RawFormData({FormSpecId("pull"): {"value": "https://agent"}}),
            ],
            [
                RawFormData({FormSpecId("mode"): {"value": "pull"}}),
                RawFormData({FormSpecId("pull"): {"value": "https://agent"}}),
            ],
            id="the form data of a shown stage is kept",
        ),
        pytest.param(
            [
                RawFormData({FormSpecId("mode"): {"value": "push"}}),
                RawFormData({FormSpecId("pull"): {"value": "https://agent"}}),
            ],
            [RawFormData({FormSpecId("mode"): {"value": "push"}}), RawFormData({})],
            id="the form data of a hidden stage is blanked",
        ),
        pytest.param(
            [RawFormData({FormSpecId("mode"): {"value": "pull"}})],
            [RawFormData({FormSpecId("mode"): {"value": "pull"}})],
            id="the form data keeps the length of the input",
        ),
    ],
)
def test_visible_form_data(
    raw_form_data: Sequence[RawFormData], expected: list[RawFormData]
) -> None:
    stages = [_stage("mode"), _stage("pull", _value_is("mode", "pull")), _stage("review")]

    _applicability_out, visible_form_data = stage_applicability_and_form_data(
        stages, raw_form_data, build_formspec_map_from_stages([stage() for stage in stages])
    )

    assert visible_form_data == expected


@pytest.mark.parametrize(
    "raw_form_data, prefill_data, expected",
    [
        pytest.param(
            [],
            {FormSpecId("mode"): {"value": "pull"}},
            [True, True],
            id="prefill data decides while no form data is submitted",
        ),
        pytest.param(
            [RawFormData({FormSpecId("mode"): {"value": "push"}})],
            {FormSpecId("mode"): {"value": "pull"}},
            [True, False],
            id="submitted form data wins over prefill data",
        ),
    ],
)
def test_prefill_data(
    raw_form_data: Sequence[RawFormData],
    prefill_data: ParsedFormData,
    expected: list[bool],
) -> None:
    stages = [_stage("mode"), _stage("pull", _value_is("mode", "pull"))]

    applicability, _visible_form_data = stage_applicability_and_form_data(
        stages,
        raw_form_data,
        build_formspec_map_from_stages([stage() for stage in stages]),
        prefill_data=prefill_data,
    )

    assert applicability == expected


def test_submitted_form_data_without_a_stage_is_kept() -> None:
    stages = [_stage("mode"), _stage("pull", _value_is("mode", "pull"))]
    raw_form_data = [
        RawFormData({FormSpecId("mode"): {"value": "pull"}}),
        RawFormData({FormSpecId("pull"): {"value": "https://agent"}}),
        RawFormData({FormSpecId("beyond"): {"value": "extra"}}),
    ]

    _applicability, visible_form_data = stage_applicability_and_form_data(
        stages, raw_form_data, build_formspec_map_from_stages([stage() for stage in stages])
    )

    assert visible_form_data == raw_form_data


def test_no_stage_is_built_while_nothing_is_submitted() -> None:
    def _exploding_factory() -> QuickSetupStage:
        raise AssertionError("No stage may be built to decide the applicability")

    stages: list[StageFactory] = [
        _stage("mode"),
        applicable_if(_value_is("mode", "pull"))(_exploding_factory),
    ]

    applicability, _visible_form_data = stage_applicability_and_form_data(
        stages, [], {}, prefill_data={FormSpecId("mode"): {"value": "pull"}}
    )

    assert applicability == [True, True]


@pytest.mark.parametrize(
    "first_stage, raw_form_data, expected",
    [
        pytest.param(
            _stage("mode", elements=("value", "other")),
            [RawFormData({FormSpecId("mode"): {"value": "pull", "other": 5}})],
            [True, False],
            id="an invalid element drops the whole form spec",
        ),
        pytest.param(
            _stage("mode", second_form_spec_id="host"),
            [
                RawFormData(
                    {FormSpecId("mode"): {"value": "pull"}, FormSpecId("host"): {"value": 5}}
                )
            ],
            [True, True],
            id="an invalid form spec does not affect another form spec",
        ),
    ],
)
def test_invalid_form_data_granularity(
    first_stage: StageFactory,
    raw_form_data: Sequence[RawFormData],
    expected: list[bool],
) -> None:
    """A form spec is validated and parsed as a whole, so it is dropped as a whole."""
    stages = [first_stage, _stage("pull", _value_is("mode", "pull"))]

    applicability, _visible_form_data = stage_applicability_and_form_data(
        stages, raw_form_data, build_formspec_map_from_stages([stage() for stage in stages])
    )

    assert applicability == expected


def test_every_stage_applies_if_no_stage_has_a_condition() -> None:
    stages = [_stage("mode"), _stage("push"), _stage("review")]
    raw_form_data = [
        RawFormData({FormSpecId("mode"): {"value": "push"}}),
        RawFormData({FormSpecId("push"): {"value": "collector"}}),
    ]

    applicability, visible_form_data = stage_applicability_and_form_data(
        stages, raw_form_data, build_formspec_map_from_stages([stage() for stage in stages])
    )

    assert applicability == [True, True, True]
    assert visible_form_data == raw_form_data


def test_condition_on_the_first_stage_is_ignored() -> None:
    stages = [_stage("mode", _value_is("mode", "never")), _stage("review")]

    applicability, _visible_form_data = stage_applicability_and_form_data(
        stages,
        [RawFormData({FormSpecId("mode"): {"value": "push"}})],
        build_formspec_map_from_stages([stage() for stage in stages]),
    )

    assert applicability == [True, True]

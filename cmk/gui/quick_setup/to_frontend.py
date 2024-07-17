#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from dataclasses import asdict
from typing import cast, Mapping

from cmk.utils.quick_setup.definitions import (
    FormData,
    IncomingStage,
    InvalidStageException,
    QuickSetup,
    QuickSetupOverview,
    QuickSetupSaveRedirect,
    QuickSetupStage,
    Stage,
    StageId,
)
from cmk.utils.quick_setup.widgets import (
    Collapsible,
    FormSpecId,
    FormSpecRecap,
    FormSpecWrapper,
    ListOfWidgets,
    Widget,
)

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.type_defs import DataOrigin

from cmk.rulesets.v1.form_specs import FormSpec


def _get_stage_components_from_widget(widget: Widget) -> dict:
    if isinstance(widget, (ListOfWidgets, Collapsible)):
        widget_as_dict = asdict(widget)
        widget_as_dict["items"] = [_get_stage_components_from_widget(item) for item in widget.items]
        return widget_as_dict

    if isinstance(widget, FormSpecWrapper):
        form_spec = cast(FormSpec, widget.form_spec)
        return {
            "widget_type": widget.widget_type,
            "form_spec": asdict(
                serialize_data_for_frontend(
                    form_spec=form_spec,
                    field_id=str(widget.id),
                    origin=DataOrigin.DISK,
                    do_validate=False,
                ),
            ),
        }

    return asdict(widget)


def _retrieve_next_stage(
    quick_setup: QuickSetup,
    current_stage: QuickSetupStage,
    incoming_stages: Sequence[IncomingStage],
) -> Stage:
    try:
        next_stage = quick_setup.get_stage_with_id(StageId(current_stage.stage_id + 1))
    except InvalidStageException:
        # TODO: What should we return in this case?
        return Stage(stage_id=StageId(-1), components=[])

    return Stage(
        stage_id=next_stage.stage_id,
        components=[
            _get_stage_components_from_widget(widget) for widget in next_stage.configure_components
        ],
        stage_recap=[
            r
            for recap_callable in current_stage.recap
            for r in recap_callable([stage.form_data for stage in incoming_stages])
        ],
    )


def form_spec_validate(
    all_stages_form_data: Sequence[FormData],
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> list[str]:
    validation_errors: list = []
    last_stage = all_stages_form_data[-1]
    for form_spec_id, form_data in last_stage.items():
        try:
            form_spec = expected_formspecs_map[form_spec_id]
            serialize_data_for_frontend(
                form_spec=form_spec,
                field_id=form_spec_id,
                origin=DataOrigin.FRONTEND,
                do_validate=True,
                value=form_data,
            )

        # TODO: What does a validation error look like, and how should they be returned to the frontend?
        except (AssertionError, AttributeError, KeyError) as exc:
            validation_errors.append(str(exc))
    return validation_errors


def _flatten_formspec_wrappers(components: Sequence[Widget]) -> Iterator[FormSpecWrapper]:
    for component in components:
        if isinstance(component, (ListOfWidgets, Collapsible)):
            yield from iter(_flatten_formspec_wrappers(component.items))

        if isinstance(component, FormSpecWrapper):
            yield component


def _build_expected_formspec_map(quick_setup: QuickSetup) -> Mapping[FormSpecId, FormSpec]:
    return {
        widget.id: cast(FormSpec, widget.form_spec)
        for stage in quick_setup.stages
        for widget in _flatten_formspec_wrappers(stage.configure_components)
    }


def quick_setup_overview(quick_setup: QuickSetup) -> QuickSetupOverview:
    first_stage = quick_setup.get_stage_with_id(StageId(1))
    return QuickSetupOverview(
        quick_setup_id=quick_setup.id,
        overviews=[stage.stage_overview() for stage in quick_setup.stages],
        stage=Stage(
            stage_id=first_stage.stage_id,
            components=[
                _get_stage_components_from_widget(widget)
                for widget in first_stage.configure_components
            ],
        ),
    )


def form_spec_recap(stages_form_data: Sequence[FormData]) -> Sequence[Widget]:
    return [FormSpecRecap(id=form_spec_id) for form_spec_id in stages_form_data[-1]]


def validate_current_stage(
    quick_setup: QuickSetup, incoming_stages: Sequence[IncomingStage]
) -> Stage:
    current_stage_id = incoming_stages[-1].stage_id
    current_stage = quick_setup.get_stage_with_id(current_stage_id)
    validation_errors = [
        error
        for validator in current_stage.validators
        for error in validator(
            [stage.form_data for stage in incoming_stages],
            _build_expected_formspec_map(quick_setup),
        )
    ]

    if validation_errors:
        return Stage(
            stage_id=current_stage_id,
            validation_errors=validation_errors,
            components=[],
        )

    return _retrieve_next_stage(
        quick_setup=quick_setup,
        current_stage=current_stage,
        incoming_stages=incoming_stages,
    )


def complete_quick_setup(
    quick_setup: QuickSetup,
    stages: Sequence[IncomingStage],
) -> QuickSetupSaveRedirect:
    if quick_setup.save_action is None:
        return QuickSetupSaveRedirect(redirect_url=None)
    return QuickSetupSaveRedirect(redirect_url=quick_setup.save_action(stages))

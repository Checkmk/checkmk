#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, MutableSequence, Sequence
from dataclasses import asdict
from typing import cast, Mapping

from cmk.utils.quick_setup.definitions import (
    Errors,
    FormData,
    GeneralStageErrors,
    IncomingStage,
    InvalidStageException,
    QuickSetup,
    QuickSetupOverview,
    QuickSetupSaveRedirect,
    QuickSetupStage,
    Stage,
    StageId,
    ValidationErrorMap,
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


def form_spec_validate(
    all_stages_form_data: Sequence[FormData],
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> tuple[ValidationErrorMap, GeneralStageErrors]:
    general_errors: GeneralStageErrors = []
    validation_errors: ValidationErrorMap = {}
    last_stage = all_stages_form_data[-1]
    for formspec_id, form_data in last_stage.items():
        if formspec_id not in expected_formspecs_map:
            general_errors.append(f"Formspec id '{formspec_id}' not found")
            continue

        try:
            form_spec = expected_formspecs_map[formspec_id]
            result = serialize_data_for_frontend(
                form_spec=form_spec,
                field_id=formspec_id,
                origin=DataOrigin.FRONTEND,
                do_validate=True,
                value=form_data,
            )
            if result.validation:
                validation_errors[formspec_id] = result.validation
        except (AssertionError, AttributeError) as exc:
            general_errors.append(str(exc))

    return validation_errors, general_errors


def _flatten_formspec_wrappers(components: Sequence[Widget]) -> Iterator[FormSpecWrapper]:
    for component in components:
        if isinstance(component, (ListOfWidgets, Collapsible)):
            yield from iter(_flatten_formspec_wrappers(component.items))

        if isinstance(component, FormSpecWrapper):
            yield component


def build_expected_formspec_map(stages: Sequence[QuickSetupStage]) -> Mapping[FormSpecId, FormSpec]:
    return {
        widget.id: cast(FormSpec, widget.form_spec)
        for stage in stages
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
            button_txt=first_stage.button_txt,
        ),
    )


def form_spec_recaps(
    stages_form_data: Sequence[FormData],
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> Sequence[Widget]:

    recap: MutableSequence[Widget] = []
    for formspec_id, form_data in stages_form_data[-1].items():
        if formspec_id not in expected_formspecs_map:
            continue

        form_spec = expected_formspecs_map[formspec_id]
        result = serialize_data_for_frontend(
            form_spec=form_spec,
            field_id=formspec_id,
            origin=DataOrigin.FRONTEND,
            do_validate=False,
            value=form_data,
        )
        recap.append(FormSpecRecap(id=formspec_id, form_spec=result))
    return recap


def validate_current_stage(
    quick_setup: QuickSetup,
    incoming_stages: Sequence[IncomingStage],
) -> Stage | None:
    current_stage_id = incoming_stages[-1].stage_id
    current_stage = quick_setup.get_stage_with_id(current_stage_id)

    errors = Errors()
    for validator in current_stage.validators:
        errors_formspec, errors_stage = validator(
            [stage.form_data for stage in incoming_stages],
            build_expected_formspec_map(quick_setup.stages),
        )
        for form_spec_id, fs_errors in errors_formspec.items():
            errors.formspec_errors.setdefault(form_spec_id, [])
            errors.formspec_errors[form_spec_id].extend(fs_errors)

        errors.stage_errors.extend(errors_stage)

    if errors.formspec_errors or errors.stage_errors:
        return Stage(
            stage_id=current_stage_id,
            errors=errors,
            components=[],
            button_txt=None,
        )
    return None


def retrieve_next_stage(
    quick_setup: QuickSetup,
    incoming_stages: Sequence[IncomingStage],
) -> Stage:
    current_stage_id = incoming_stages[-1].stage_id
    current_stage = quick_setup.get_stage_with_id(current_stage_id)

    try:
        next_stage = quick_setup.get_stage_with_id(StageId(current_stage.stage_id + 1))
    except InvalidStageException:
        # TODO: What should we return in this case?
        return Stage(stage_id=StageId(-1), components=[], button_txt=None)

    return Stage(
        stage_id=next_stage.stage_id,
        components=[
            _get_stage_components_from_widget(widget) for widget in next_stage.configure_components
        ],
        stage_recap=[
            r
            for recap_callable in current_stage.recap
            for r in recap_callable(
                [stage.form_data for stage in incoming_stages],
                build_expected_formspec_map(quick_setup.stages),
            )
        ],
        button_txt=next_stage.button_txt,
    )


def complete_quick_setup(
    quick_setup: QuickSetup,
    stages: Sequence[IncomingStage],
) -> QuickSetupSaveRedirect:
    if quick_setup.save_action is None:
        return QuickSetupSaveRedirect(redirect_url=None)
    return QuickSetupSaveRedirect(redirect_url=quick_setup.save_action(stages))

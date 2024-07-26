#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, MutableSequence, Sequence
from dataclasses import asdict
from typing import Any, cast, Mapping

from cmk.utils.quick_setup.definitions import (
    Errors,
    GeneralStageErrors,
    IncomingStage,
    InvalidStageException,
    ParsedFormData,
    QuickSetup,
    QuickSetupOverview,
    QuickSetupSaveRedirect,
    QuickSetupStage,
    QuickSetupValidationError,
    RawFormData,
    Stage,
    StageId,
    UniqueBundleIDStr,
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

from cmk.gui.form_specs.vue.form_spec_visitor import (
    parse_value_from_frontend,
    serialize_data_for_frontend,
    validate_value_from_frontend,
)
from cmk.gui.form_specs.vue.type_defs import DataOrigin
from cmk.gui.watolib.configuration_bundles import ConfigBundleStore

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


def _stage_validate_all_form_spec_keys_existing(
    current_stage_form_data: RawFormData,
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> GeneralStageErrors:
    return [
        f"Formspec id '{form_spec_id}' not found"
        for form_spec_id in current_stage_form_data.keys()
        if form_spec_id not in expected_formspecs_map
    ]


def _form_spec_validate(
    all_stages_form_data: Sequence[RawFormData],
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> ValidationErrorMap:
    return {
        form_spec_id: [QuickSetupValidationError(**asdict(error)) for error in errors]
        for current_stage_form_data in all_stages_form_data
        for form_spec_id, form_data in current_stage_form_data.items()
        if (errors := validate_value_from_frontend(expected_formspecs_map[form_spec_id], form_data))
    }


def _form_spec_parse(
    all_stages_form_data: Sequence[RawFormData],
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> ParsedFormData:
    return {
        form_spec_id: parse_value_from_frontend(expected_formspecs_map[form_spec_id], form_data)
        for current_stage_form_data in all_stages_form_data
        for form_spec_id, form_data in current_stage_form_data.items()
    }


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


def _find_unique_id(form_data: Any, target_key: str) -> None | str:
    if isinstance(form_data, dict):
        for key, value in form_data.items():
            if key == target_key:
                return value
            result = _find_unique_id(value, target_key)
            if result is not None:
                return result
        return None
    if isinstance(form_data, list):
        for item in form_data:
            result = _find_unique_id(item, target_key)
            if result is not None:
                return result
    return None


def validate_unique_id(
    stages_form_data: ParsedFormData,
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> tuple[ValidationErrorMap, GeneralStageErrors]:
    bundle_id = _find_unique_id(stages_form_data, UniqueBundleIDStr)
    if bundle_id is None:
        return {}, [f"Expected the key '{UniqueBundleIDStr}' in the form data"]

    if bundle_id in ConfigBundleStore().load_for_reading():
        return {}, [f'Configuration bundle "{bundle_id}" already exists.']

    return {}, []


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
    stages_form_data: Sequence[RawFormData],
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
    expected_form_spec_map = build_expected_formspec_map(quick_setup.stages)
    form_data = [stage.form_data for stage in incoming_stages]
    errors.stage_errors.extend(
        _stage_validate_all_form_spec_keys_existing(form_data[-1], expected_form_spec_map)
    )
    errors.formspec_errors = _form_spec_validate(form_data, expected_form_spec_map)
    if errors.formspec_errors or errors.stage_errors:
        return Stage(
            stage_id=current_stage_id,
            errors=errors,
            components=[],
            button_txt=None,
        )
    combined_parsed_form_data_up_to_current_stage = _form_spec_parse(
        form_data, expected_form_spec_map
    )

    for validator in current_stage.validators:
        errors_formspec, errors_stage = validator(
            combined_parsed_form_data_up_to_current_stage,
            expected_form_spec_map,
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

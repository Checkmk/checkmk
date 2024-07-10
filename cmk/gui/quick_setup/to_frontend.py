#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict
from typing import cast

from cmk.utils.quick_setup.definitions import (
    IncomingStage,
    InvalidStageException,
    QuickSetup,
    QuickSetupOverview,
    QuickSetupSaveRedirect,
    QuickSetupStage,
    Stage,
    StageId,
)
from cmk.utils.quick_setup.widgets import FormSpecWrapper, ListOfWidgets, Widget

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.type_defs import DataOrigin

from cmk.rulesets.v1.form_specs import FormSpec


def get_stage_components_from_widget(widget: Widget) -> dict:
    if isinstance(widget, ListOfWidgets):
        widget_as_dict = asdict(widget)
        widget_as_dict["items"] = [get_stage_components_from_widget(item) for item in widget.items]
        return widget_as_dict
    return asdict(widget)


def get_stage_components_for_the_frontend(
    quick_setup_stage: QuickSetupStage,
) -> list[dict]:
    components: list[dict] = []
    for widget in quick_setup_stage.components:
        if isinstance(widget, FormSpecWrapper):
            form_spec = cast(FormSpec, widget.form_spec)
            components.append(
                asdict(
                    serialize_data_for_frontend(
                        form_spec=form_spec,
                        field_id=widget.id,
                        origin=DataOrigin.DISK,
                        do_validate=False,
                    ),
                ),
            )
        else:
            components.append(get_stage_components_from_widget(widget))
    return components


def retrieve_next_stage(
    quick_setup: QuickSetup,
    current_stage_id: StageId,
) -> Stage:
    try:
        next_stage = quick_setup.get_stage_with_id(StageId(current_stage_id + 1))
    except InvalidStageException:
        # TODO: What should we return in this case?
        return Stage(stage_id=StageId(-1), components=[])

    return Stage(
        stage_id=next_stage.stage_id,
        components=get_stage_components_for_the_frontend(next_stage),
    )


def form_spec_validate(
    quick_setup_stage: QuickSetupStage,
    form_data: dict,
) -> list[str]:
    validation_errors: list = []
    for widget in quick_setup_stage.components:
        if isinstance(widget, FormSpecWrapper):
            form_spec = cast(FormSpec, widget.form_spec)
            try:
                serialize_data_for_frontend(
                    form_spec=form_spec,
                    field_id=widget.id,
                    origin=DataOrigin.FRONTEND,
                    do_validate=True,
                    value=form_data[widget.id],
                )
            # TODO: What does a validation error look like, and how should they be returned to the frontend?
            except (AssertionError, AttributeError) as exc:
                validation_errors.append(str(exc))

    return validation_errors


def quick_setup_overview(quick_setup: QuickSetup) -> QuickSetupOverview:
    first_stage = quick_setup.get_stage_with_id(StageId(1))
    return QuickSetupOverview(
        quick_setup_id=quick_setup.id,
        overviews=[stage.stage_overview() for stage in quick_setup.stages],
        stage=Stage(
            stage_id=first_stage.stage_id,
            components=get_stage_components_for_the_frontend(first_stage),
        ),
    )


def validate_current_stage(
    quick_setup: QuickSetup,
    stages: list[IncomingStage],
) -> Stage:
    current_stage_id = StageId(0)
    current_stage_form_data: dict = {}

    for stage in stages:
        if stage.stage_id > current_stage_id:
            current_stage_id = stage.stage_id
            current_stage_form_data = stage.form_data

    current_stage = quick_setup.get_stage_with_id(current_stage_id)
    validation_errors = form_spec_validate(current_stage, current_stage_form_data)
    if validation_errors:
        return Stage(
            stage_id=current_stage_id,
            components=get_stage_components_for_the_frontend(current_stage),
            validation_errors=validation_errors,
        )

    return retrieve_next_stage(quick_setup=quick_setup, current_stage_id=current_stage_id)


def complete_quick_setup(
    quick_setup: QuickSetup,
    stages: list[IncomingStage],
) -> QuickSetupSaveRedirect:
    if quick_setup.save_action is None:
        return QuickSetupSaveRedirect(redirect_url=None)
    return QuickSetupSaveRedirect(redirect_url=quick_setup.save_action(stages))

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, MutableMapping, MutableSequence, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, cast

from pydantic import BaseModel

from cmk.ccc.i18n import _

from cmk.gui.form_specs.vue.form_spec_visitor import (
    parse_value_from_frontend,
    serialize_data_for_frontend,
)
from cmk.gui.form_specs.vue.visitors import DataOrigin, DEFAULT_VALUE
from cmk.gui.quick_setup.private.widgets import ConditionalNotificationStageWidget
from cmk.gui.quick_setup.v0_unstable.setups import CallableValidator, FormspecMap
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ActionId,
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
    RawFormData,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import (
    Collapsible,
    FormSpecId,
    FormSpecWrapper,
    ListOfWidgets,
    Widget,
)

from cmk.rulesets.v1.form_specs import FormSpec

LOAD_WAIT_LABEL = _("Please wait...")
PREV_BUTTON_LABEL = _("Back")
PREV_BUTTON_ARIA_LABEL = _("Go to the previous stage")
NEXT_BUTTON_LABEL = _("Next")
NEXT_BUTTON_ARIA_LABEL = _("Go to the next stage")


@dataclass
class Button:
    label: str
    aria_label: str


@dataclass
class Action:
    id: ActionId
    button: Button
    load_wait_label: str = field(default=LOAD_WAIT_LABEL)


def form_spec_parse(
    all_stages_form_data: Sequence[RawFormData],
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> ParsedFormData:
    return {
        form_spec_id: parse_value_from_frontend(expected_formspecs_map[form_spec_id], form_data)
        for current_stage_form_data in all_stages_form_data
        for form_spec_id, form_data in current_stage_form_data.items()
    }


def get_stage_components_from_widget(widget: Widget, prefill_data: ParsedFormData | None) -> dict:
    if isinstance(widget, (ListOfWidgets, Collapsible, ConditionalNotificationStageWidget)):
        widget_as_dict = asdict(widget)
        widget_as_dict["items"] = [
            get_stage_components_from_widget(item, prefill_data) for item in widget.items
        ]
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
                    value=prefill_data.get(widget.id) if prefill_data else DEFAULT_VALUE,
                    do_validate=False,
                )
            ),
        }

    return asdict(widget)


@dataclass
class QuickSetupValidationError:
    message: str
    invalid_value: Any
    location: Sequence[str] = field(default_factory=list)


ValidationErrorMap = MutableMapping[FormSpecId, MutableSequence[QuickSetupValidationError]]


@dataclass
class ValidationErrors:
    """Data class representing errors that occurred during the validation process

    Attributes:
        stage_index:
            The index of the stage where the error occurred. If None, the error is stage independent
            (for example a Quick setup (not stage) custom validation failed when attempting to
            perform the complete action)
        formspec_errors:
            A mapping of form spec ids to a list of validation errors that occurred for the
            respective form spec. These are usually stage specific
        stage_errors:
            A list of general stage errors that occurred during the validation process (besides the
            formspecs)
    """

    stage_index: StageIndex | None
    formspec_errors: ValidationErrorMap = field(default_factory=dict)
    stage_errors: GeneralStageErrors = field(default_factory=list)

    def exist(self) -> bool:
        return bool(self.formspec_errors or self.stage_errors)


def validate_custom_validators(
    quick_setup_id: QuickSetupId,
    custom_validators: Iterable[CallableValidator],
    stages_raw_formspecs: Sequence[RawFormData],
    quick_setup_formspec_map: FormspecMap,
) -> ValidationErrors:
    errors = ValidationErrors(stage_index=None)
    for custom_validator in custom_validators:
        errors.stage_errors.extend(
            custom_validator(
                quick_setup_id,
                form_spec_parse(stages_raw_formspecs, quick_setup_formspec_map),
            )
        )
    return errors


class BackgroundJobException(BaseModel):
    message: str
    traceback: str

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import enum
from collections.abc import Iterable, Mapping, MutableMapping, MutableSequence, Sequence
from dataclasses import asdict, dataclass, field
from typing import cast

from pydantic import BaseModel

from cmk.gui.background_job.job import BackgroundProcessInterface
from cmk.gui.exceptions import MKInternalError
from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    RawDiskData,
    RawFrontendData,
    serialize_data_for_frontend,
    VisitorOptions,
)
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.log import logger
from cmk.gui.quick_setup.private.widgets import ConditionalNotificationStageWidget
from cmk.gui.quick_setup.v0_unstable.setups import (
    CallableStageApplicability,
    CallableValidator,
    ConditionalStage,
    FormspecMap,
    ProgressLogger,
    QuickSetupContext,
    StageFactory,
    StepStatus,
)
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
class ProgressStep:
    title: str
    status: StepStatus
    index: int


@dataclass
class ProgressState:
    steps: Sequence[ProgressStep]


class InfoLogger:
    @staticmethod
    def log_new_progress_step(
        step_name: str,
        step_title: str,  # noqa: ARG004
        status: StepStatus = StepStatus.ACTIVE,
    ) -> None:
        logger.info(f"[QuickSetup] {step_name} - {status}")

    @staticmethod
    def update_progress_step_status(step_name: str, status: StepStatus) -> None:
        logger.info(f"[QuickSetup] {step_name} - {status}")


class JobBasedProgressLogger:
    """Class which makes use of the background job send_progress mechanism to log
    Quick setup specific progress steps.

    The logged Quick setup progress steps are visible to the user who triggered the Quick
    setup (stage) action.

    Notes:
        * The Quick setup progress logged via this class will be distinguishable to other
        background job update logs through a [QuickSetup] prefix

    """

    def __init__(self, progress_interface: BackgroundProcessInterface):
        self._progress_interface = progress_interface
        self._steps: dict[str, ProgressStep] = {}

    def log_new_progress_step(
        self, step_name: str, step_title: str, status: StepStatus = StepStatus.ACTIVE
    ) -> None:
        """Log a new progress step which will be displayed to the user

        Attributes:
            step_name:
                A unique identifier for the progress step
            step_title:
                The title of the progress step. This will be visible to the user who triggered
                the Quick setup (stage) action
            status:
                The status determines the rendering of the progress step
                Defaults to StepStatus.ACTIVE

        Notes:
            * A new progress step should be updated to StepStatus.COMPLETED at some point in the
            Quick setup flow

        Pseudo example:
            cls.log_new_progress_step("test_connection", "Test connection to datasource")
            # do test connection related stuff
            cls.update_progress_step_status("test_connection", StepStatus.COMPLETED)
        """
        # TODO: this is currently a workaround since the progress logs during a
        #  Quick setup (stage) action are shown to the user and the localization mechanism is
        #  unavailable on the VueJS side. The step_title should be a normal string once the
        #  mechanism becomes available.
        translated_title = translate_to_current_language(step_title)
        self._steps[step_name] = ProgressStep(
            title=translated_title, status=status, index=len(self._steps)
        )
        self._log_progress()

    def update_progress_step_status(self, step_name: str, status: StepStatus) -> None:
        self._steps[step_name].status = status
        self._log_progress()

    def _log_progress(self) -> None:
        ordered_steps = sorted(self._steps.values(), key=lambda step: step.index)
        state = ProgressState(steps=ordered_steps)
        self._progress_interface.send_progress_update(
            "[QuickSetup] %s"
            % asdict(
                state,
                dict_factory=lambda x: {
                    k: (v.value if isinstance(v, enum.Enum) else v) for k, v in x
                },
            )
        )


@dataclass
class ButtonIcon:
    name: str
    rotate: int


@dataclass
class Button:
    label: str
    aria_label: str
    icon: ButtonIcon | None = None


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
        form_spec_id: get_visitor(
            expected_formspecs_map[form_spec_id],
            VisitorOptions(migrate_values=True, mask_values=False),
        ).to_disk(RawFrontendData(form_data))
        for current_stage_form_data in all_stages_form_data
        for form_spec_id, form_data in current_stage_form_data.items()
    }


def stage_applicability_and_form_data(
    stage_factories: Sequence[StageFactory],
    stages_raw_form_data: Sequence[RawFormData],
    quick_setup_formspec_map: FormspecMap,
    *,
    prefill_data: ParsedFormData | None = None,
) -> tuple[list[bool], list[RawFormData]]:
    """Determine which stages are shown and blank out the form data of the hidden ones.

    The conditions are read from the stage factories, so no stage is built here. The formspec
    map only parses `stages_raw_form_data`, so it can be empty while nothing is submitted.

    Returns one applicability per stage, and the form data with the entries of the hidden stages
    replaced by an empty mapping. The second list has as many entries as `stages_raw_form_data`.
    """
    conditions = [ConditionalStage.condition_of(factory) for factory in stage_factories]
    if all(condition is None for condition in conditions):
        return [True] * len(conditions), list(stages_raw_form_data)

    applicability: list[bool] = []
    visible_raw_form_data: list[RawFormData] = []

    for stage_index, condition in enumerate(conditions):
        is_applicable = (
            stage_index == 0
            or condition is None
            or _condition_holds(
                condition,
                getattr(stage_factories[stage_index], "__name__", "<stage>"),
                {
                    **(prefill_data or {}),
                    **_parse_condition_input(visible_raw_form_data, quick_setup_formspec_map),
                },
            )
        )
        applicability.append(is_applicable)
        if stage_index < len(stages_raw_form_data):
            visible_raw_form_data.append(
                stages_raw_form_data[stage_index] if is_applicable else RawFormData({})
            )

    visible_raw_form_data.extend(stages_raw_form_data[len(conditions) :])
    return applicability, visible_raw_form_data


def _parse_condition_input(
    stages_raw_form_data: Sequence[RawFormData],
    quick_setup_formspec_map: FormspecMap,
) -> ParsedFormData:
    """Parse the form data a stage condition may read.

    A condition runs before the form data is validated, so an unknown or invalid field is
    skipped instead of parsed.
    """
    return form_spec_parse(
        [
            RawFormData(
                {
                    form_spec_id: form_data
                    for form_spec_id, form_data in stage_raw_form_data.items()
                    if form_spec_id in quick_setup_formspec_map
                    and not get_visitor(
                        quick_setup_formspec_map[form_spec_id],
                        VisitorOptions(migrate_values=True, mask_values=False),
                    ).validate(RawFrontendData(form_data))
                }
            )
            for stage_raw_form_data in stages_raw_form_data
        ],
        quick_setup_formspec_map,
    )


def _condition_holds(
    condition: CallableStageApplicability,
    stage_name: str,
    parsed_form_data: ParsedFormData,
) -> bool:
    """Evaluate a stage condition. A condition that raises hides its stage."""
    try:
        return condition(parsed_form_data)
    except Exception:
        logger.warning(
            "Applicability condition of Quick setup stage %(stage_name)s failed. "
            "The stage is hidden.",
            {"stage_name": stage_name},
            exc_info=True,
        )
        return False


def get_stage_components_from_widget(widget: Widget, prefill_data: ParsedFormData | None) -> dict:
    if isinstance(widget, ListOfWidgets | Collapsible | ConditionalNotificationStageWidget):
        widget_as_dict = asdict(widget)
        widget_as_dict["items"] = [
            get_stage_components_from_widget(item, prefill_data) for item in widget.items
        ]
        if isinstance(widget, Collapsible) and (items := widget_as_dict.get("items", [])):
            widget_as_dict["open"] = any(
                item.get("form_spec", {}).get("data", {}) for item in items
            )
        return widget_as_dict

    if isinstance(widget, FormSpecWrapper):
        form_spec = cast(FormSpec, widget.form_spec)
        return {
            "widget_type": widget.widget_type,
            "form_spec": asdict(
                serialize_data_for_frontend(
                    form_spec=form_spec,
                    field_id=str(widget.id),
                    value=(
                        RawDiskData(prefill_data.get(widget.id)) if prefill_data else DEFAULT_VALUE
                    ),
                    do_validate=False,
                )
            ),
        }

    return asdict(widget)


@dataclass
class QuickSetupValidationError:
    message: str
    replacement_value: object
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
    progress_logger: ProgressLogger,
    ctx: QuickSetupContext,
) -> ValidationErrors:
    errors = ValidationErrors(stage_index=None)
    for custom_validator in custom_validators:
        errors.stage_errors.extend(
            custom_validator(
                quick_setup_id,
                form_spec_parse(stages_raw_formspecs, quick_setup_formspec_map),
                progress_logger,
                ctx,
            )
        )
    return errors


class BackgroundJobException(BaseModel):
    message: str
    traceback: str


class MKJobNotFoundException(MKInternalError):
    pass

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import traceback
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobDefines,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.exceptions import MKInternalError, MKUserError
from cmk.gui.form_specs.vue.form_spec_visitor import (
    validate_value_from_frontend,
)
from cmk.gui.logged_in import user
from cmk.gui.quick_setup.config_setups import register as register_config_setups
from cmk.gui.quick_setup.handlers.utils import (
    Action,
    BackgroundJobException,
    Button,
    form_spec_parse,
    get_stage_components_from_widget,
    LOAD_WAIT_LABEL,
    NEXT_BUTTON_ARIA_LABEL,
    NEXT_BUTTON_LABEL,
    PREV_BUTTON_ARIA_LABEL,
    QuickSetupValidationError,
    validate_custom_validators,
    ValidationErrorMap,
    ValidationErrors,
)
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.predefined import (
    build_formspec_map_from_stages,
    stage_components,
)
from cmk.gui.quick_setup.v0_unstable.setups import (
    FormspecMap,
    QuickSetup,
    QuickSetupStage,
    QuickSetupStageAction,
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
    FormSpecId,
    Widget,
)

from cmk.rulesets.v1.form_specs import FormSpec


class InvalidStageException(MKGeneralException):
    pass


# TODO: This dataclass is already defined in
# cmk.gui.form_specs.vue.autogen_type_defs.vue_formspec_components
# but can't be imported here. Once we move this module, we can remove this
# and use the one from the other module.


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
    current_stage_form_data: RawFormData,
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> ValidationErrorMap:
    return {
        form_spec_id: [QuickSetupValidationError(**asdict(error)) for error in errors]
        for form_spec_id, form_data in current_stage_form_data.items()
        if (errors := validate_value_from_frontend(expected_formspecs_map[form_spec_id], form_data))
    }


def matching_stage_action(
    stage: QuickSetupStage, stage_action_id: ActionId
) -> QuickSetupStageAction:
    for action in stage.actions:
        if action.id == stage_action_id:
            return action
    raise InvalidStageException(f"Stage action '{stage_action_id}' not found")


def verify_stage_custom_validators(
    quick_setup: QuickSetup,
    stages_raw_formspecs: Sequence[RawFormData],
    stage_index: StageIndex,
    stage_action_id: ActionId,
    stages: Sequence[QuickSetupStage],
    quick_setup_formspec_map: FormspecMap,
) -> ValidationErrors | None:
    """Verify that the custom validators pass of a Quick setup stage.

    Args:
        quick_setup:
            The quick setup object.

        stages_raw_formspecs:
            The form data of all stages (the user input)

        stage_index:
            The index of the stage to validate.

        stage_action_id:
            The id of the stage action to validate against

        stages:
            The stages of the quick setup.

        quick_setup_formspec_map:
            The form spec map of the quick setup across all stages. This map is based on the stages
            definition
    """
    errors = ValidationErrors(stage_index=stage_index)
    custom_validators = matching_stage_action(
        stages[stage_index], stage_action_id
    ).custom_validators
    errors.stage_errors.extend(
        validate_custom_validators(
            quick_setup.id, custom_validators, stages_raw_formspecs, quick_setup_formspec_map
        ).stage_errors
    )
    return errors if errors.exist() else None


def validate_stage_formspecs(
    stage_index: StageIndex,
    stages_raw_formspecs: Sequence[RawFormData],
    quick_setup_formspec_map: FormspecMap,
) -> ValidationErrors:
    errors = ValidationErrors(stage_index=stage_index)
    errors.stage_errors.extend(
        _stage_validate_all_form_spec_keys_existing(
            stages_raw_formspecs[stage_index], quick_setup_formspec_map
        )
    )
    if errors.exist():
        return errors

    errors.formspec_errors = _form_spec_validate(
        stages_raw_formspecs[stage_index],
        quick_setup_formspec_map,
    )
    return errors


def recap_stage(
    quick_setup_id: QuickSetupId,
    stage_index: StageIndex,
    stages: Sequence[QuickSetupStage],
    stage_action_id: ActionId,
    stages_raw_formspecs: Sequence[RawFormData],
    quick_setup_formspec_map: FormspecMap,
) -> Sequence[Widget]:
    parsed_formspec = form_spec_parse(stages_raw_formspecs, quick_setup_formspec_map)
    recap_widgets: list[Widget] = []
    for recap_callable in matching_stage_action(stages[stage_index], stage_action_id).recap:
        recap_widgets.extend(
            recap_callable(
                quick_setup_id,
                stage_index,
                parsed_formspec,
            )
        )
    return recap_widgets


class StageActionResult(BaseModel, frozen=False):
    validation_errors: ValidationErrors | None = None
    # TODO: This should be a list of widgets using only Sequence[Widget] will remove all fields
    #  when the data is returned (this is a temporary fix)
    stage_recap: Sequence[Any] = field(default_factory=list)
    background_job_exception: BackgroundJobException | None = None

    @classmethod
    def load_from_job_result(cls, job_id: str) -> "StageActionResult":
        work_dir = str(Path(BackgroundJobDefines.base_dir) / job_id)
        if not os.path.exists(work_dir):
            raise MKInternalError(None, _("Stage action result not found"))
        content = store.load_text_from_file(cls._file_path(work_dir))
        try:
            return cls.model_validate_json(content)
        except ValidationError as e:
            raise MKInternalError(
                None, f"Error reading stage action result with content: {content}"
            ) from e

    def save_to_file(self, work_dir: str) -> None:
        store.save_text_to_file(self._file_path(work_dir), self.model_dump_json())

    @staticmethod
    def _file_path(work_dir: str) -> str:
        return os.path.join(
            work_dir,
            "validation_and_recap_result.json",
        )


def verify_custom_validators_and_recap_stage(
    quick_setup: QuickSetup,
    stage_index: StageIndex,
    stage_action_id: ActionId,
    input_stages: Sequence[dict],
    form_spec_map: FormspecMap,
    built_stages: Sequence[QuickSetupStage],
) -> StageActionResult:
    response = StageActionResult()
    if (
        errors := verify_stage_custom_validators(
            quick_setup=quick_setup,
            stages_raw_formspecs=[RawFormData(stage["form_data"]) for stage in input_stages],
            stage_index=stage_index,
            stage_action_id=stage_action_id,
            stages=built_stages,
            quick_setup_formspec_map=form_spec_map,
        )
    ) is not None:
        response.validation_errors = errors
        return response

    response.stage_recap = recap_stage(
        quick_setup_id=quick_setup.id,
        stage_index=stage_index,
        stages=built_stages,
        stage_action_id=stage_action_id,
        stages_raw_formspecs=[RawFormData(stage["form_data"]) for stage in input_stages],
        quick_setup_formspec_map=form_spec_map,
    )
    return response


class QuickSetupStageActionBackgroundJob(BackgroundJob):
    housekeeping_max_age_sec = 1800
    housekeeping_max_count = 10

    job_prefix = "quick_setup_stage_action"

    @classmethod
    def gui_title(cls) -> str:
        return _("Run Quick Setup Stage Action")

    @classmethod
    def create_job_id(
        cls,
        quick_setup_id: str,
        stage_index: int,
        job_uuid: str,
    ) -> str:
        return f"{cls.job_prefix}-{quick_setup_id.replace(':', '_')}-stage_{stage_index}-{job_uuid}"

    def __init__(
        self,
        job_uuid: str,
        quick_setup_id: QuickSetupId,
        action_id: ActionId,
        stage_index: StageIndex,
        user_input_stages: Sequence[dict],
    ) -> None:
        self._quick_setup_id = quick_setup_id
        self._action_id = action_id
        self._stage_index = stage_index
        self._user_input_stages = user_input_stages
        super().__init__(job_id=self.create_job_id(quick_setup_id, stage_index, job_uuid))

    def run_quick_setup_stage_action(self, job_interface: BackgroundProcessInterface) -> None:
        job_interface.get_logger().debug("Running Quick setup stage action finally")
        with job_interface.gui_context():
            try:
                self._run_quick_setup_stage_action(job_interface)
            except Exception as e:
                job_interface.get_logger().debug(
                    "Exception raised while the Quick setup stage action: %s", e
                )
                exception_message = str(e)
                job_interface.send_exception(exception_message)
                StageActionResult(
                    background_job_exception=BackgroundJobException(
                        message=exception_message, traceback=traceback.format_exc()
                    )
                ).save_to_file(job_interface.get_work_dir())

    def _run_quick_setup_stage_action(self, job_interface: BackgroundProcessInterface) -> None:
        job_interface.send_progress_update(_("Starting Quick stage action..."))

        register_config_setups(quick_setup_registry)
        quick_setup = quick_setup_registry[self._quick_setup_id]
        built_stages_up_to_index = [
            stage() for stage in quick_setup.stages[: self._stage_index + 1]
        ]
        form_spec_map = build_formspec_map_from_stages(built_stages_up_to_index)
        action_result = verify_custom_validators_and_recap_stage(
            quick_setup=quick_setup,
            stage_index=self._stage_index,
            stage_action_id=self._action_id,
            input_stages=self._user_input_stages,
            form_spec_map=form_spec_map,
            built_stages=built_stages_up_to_index,
        )

        job_interface.send_progress_update(_("Saving the result..."))
        action_result.save_to_file(job_interface.get_work_dir())
        job_interface.send_result_message("Job finished.")


def start_quick_setup_stage_job(
    quick_setup: QuickSetup,
    action_id: ActionId,
    stage_index: StageIndex,
    user_input_stages: Sequence[dict],
) -> str:
    job_uuid = str(uuid.uuid4())
    job = QuickSetupStageActionBackgroundJob(
        job_uuid=job_uuid,
        quick_setup_id=quick_setup.id,
        action_id=action_id,
        stage_index=stage_index,
        user_input_stages=user_input_stages,
    )

    job_start = job.start(
        JobTarget(
            callable=quick_setup_stage_action_job_entry_point,
            args=QuickSetupStageActionJobArgs(
                job_uuid=job_uuid,
                quick_setup_id=quick_setup.id,
                action_id=action_id,
                stage_index=stage_index,
                user_input_stages=user_input_stages,
            ),
        ),
        InitialStatusArgs(
            title=_("Running Quick setup %s stage %s action %s")
            % (quick_setup.id, stage_index, action_id),
            user=str(user.id) if user.id else None,
        ),
    )
    if job_start.is_error():
        raise MKUserError(None, str(job_start.error))

    return job.get_job_id()


class QuickSetupStageActionJobArgs(BaseModel, frozen=True):
    job_uuid: str
    quick_setup_id: QuickSetupId
    action_id: ActionId
    stage_index: StageIndex
    user_input_stages: Sequence[dict]


def quick_setup_stage_action_job_entry_point(
    job_interface: BackgroundProcessInterface, args: QuickSetupStageActionJobArgs
) -> None:
    QuickSetupStageActionBackgroundJob(
        job_uuid=args.job_uuid,
        quick_setup_id=args.quick_setup_id,
        action_id=args.action_id,
        stage_index=args.stage_index,
        user_input_stages=args.user_input_stages,
    ).run_quick_setup_stage_action(job_interface)


@dataclass
class NextStageStructure:
    components: Sequence[dict]
    actions: Sequence[Action]
    prev_button: Button | None = None


def get_stage_structure(
    stage: QuickSetupStage,
    prefill_data: ParsedFormData | None = None,
) -> NextStageStructure:
    return NextStageStructure(
        components=[
            get_stage_components_from_widget(widget, prefill_data)
            for widget in stage_components(stage)
        ],
        prev_button=Button(label=stage.prev_button_label, aria_label=PREV_BUTTON_ARIA_LABEL)
        if stage.prev_button_label
        else None,
        actions=[
            Action(
                id=action.id,
                load_wait_label=action.load_wait_label or LOAD_WAIT_LABEL,
                button=Button(
                    label=action.next_button_label or NEXT_BUTTON_LABEL,
                    aria_label=NEXT_BUTTON_ARIA_LABEL,
                ),
            )
            for action in stage.actions
        ],
    )

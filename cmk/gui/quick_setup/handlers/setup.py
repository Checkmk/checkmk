#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, ValidationError

from cmk.ccc import store
from cmk.ccc.i18n import _

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobDefines,
    BackgroundProcessInterface,
    InitialStatusArgs,
)
from cmk.gui.exceptions import MKInternalError, MKUserError
from cmk.gui.logged_in import user
from cmk.gui.quick_setup.config_setups import register as register_config_setups
from cmk.gui.quick_setup.handlers.stage import (
    NextStageStructure,
    validate_stage_formspecs,
)
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
    PREV_BUTTON_LABEL,
    validate_custom_validators,
    ValidationErrors,
)
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.definitions import QuickSetupSaveRedirect
from cmk.gui.quick_setup.v0_unstable.predefined import (
    build_formspec_map_from_stages,
    stage_components,
)
from cmk.gui.quick_setup.v0_unstable.setups import (
    FormspecMap,
    QuickSetup,
    QuickSetupAction,
    QuickSetupActionMode,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ActionId,
    ParsedFormData,
    QuickSetupId,
    RawFormData,
    StageIndex,
)

GUIDED_MODE_STRING = _("Guided mode")
OVERVIEW_MODE_STRING = _("Overview mode")
COMPLETE_BUTTON_ARIA_LABEL = _("Save")


@dataclass
class StageOverview:
    title: str
    sub_title: str | None


@dataclass
class QuickSetupOverview:
    quick_setup_id: QuickSetupId
    overviews: list[StageOverview]
    stage: NextStageStructure
    actions: list[Action]
    prev_button: Button
    mode: str = field(default="guided")
    guided_mode_string: str = field(default=GUIDED_MODE_STRING)
    overview_mode_string: str = field(default=OVERVIEW_MODE_STRING)


def quick_setup_guided_mode(
    quick_setup: QuickSetup, prefill_data: ParsedFormData | None
) -> QuickSetupOverview:
    stages = [stage() for stage in quick_setup.stages]
    return QuickSetupOverview(
        quick_setup_id=quick_setup.id,
        overviews=[
            StageOverview(
                title=stage.title,
                sub_title=stage.sub_title,
            )
            for stage in stages
        ],
        stage=NextStageStructure(
            components=[
                get_stage_components_from_widget(widget, prefill_data)
                for widget in stage_components(stages[0])
            ],
            actions=[
                Action(
                    id=action.id,
                    button=Button(
                        label=action.next_button_label or NEXT_BUTTON_LABEL,
                        aria_label=NEXT_BUTTON_ARIA_LABEL,
                    ),
                    load_wait_label=action.load_wait_label or LOAD_WAIT_LABEL,
                )
                for action in stages[0].actions
            ],
        ),
        actions=[
            Action(
                id=action.id,
                button=Button(label=action.label, aria_label=COMPLETE_BUTTON_ARIA_LABEL),
                load_wait_label=LOAD_WAIT_LABEL,
            )
            for action in quick_setup.actions
        ],
        prev_button=Button(
            label=PREV_BUTTON_LABEL,
            aria_label=PREV_BUTTON_ARIA_LABEL,
        ),
    )


@dataclass
class CompleteStage:
    title: str
    sub_title: str | None
    components: Sequence[dict]
    actions: Sequence[Action]
    prev_button: Button


@dataclass
class QuickSetupAllStages:
    quick_setup_id: QuickSetupId
    stages: list[CompleteStage]
    actions: list[Action]
    mode: str = field(default="overview")
    guided_mode_string: str = field(default=GUIDED_MODE_STRING)
    overview_mode_string: str = field(default=OVERVIEW_MODE_STRING)


def quick_setup_overview_mode(
    quick_setup: QuickSetup,
    prefill_data: ParsedFormData | None,
) -> QuickSetupAllStages:
    stages = [stage() for stage in quick_setup.stages]
    return QuickSetupAllStages(
        quick_setup_id=quick_setup.id,
        stages=[
            CompleteStage(
                title=stage.title,
                sub_title=stage.sub_title,
                components=[
                    get_stage_components_from_widget(widget, prefill_data)
                    for widget in stage_components(stage)
                ],
                # TODO: the actions as well the prev_button should be removed from the overview mode
                #  as they are not rendered. The removal must be performed alongside adjustment
                #  of the frontend code.
                actions=[
                    Action(
                        id=action.id,
                        button=Button(
                            label=action.next_button_label or NEXT_BUTTON_LABEL,
                            aria_label=NEXT_BUTTON_ARIA_LABEL,
                        ),
                        load_wait_label=action.load_wait_label or LOAD_WAIT_LABEL,
                    )
                    for action in stage.actions
                ],
                prev_button=Button(
                    label=stage.prev_button_label or PREV_BUTTON_LABEL,
                    aria_label=PREV_BUTTON_ARIA_LABEL,
                ),
            )
            for stage in stages
        ],
        actions=[
            Action(
                id=action.id,
                button=Button(
                    label=action.label,
                    aria_label=COMPLETE_BUTTON_ARIA_LABEL,
                ),
                load_wait_label=LOAD_WAIT_LABEL,
            )
            for action in quick_setup.actions
        ],
    )


def validate_stages_form_data(
    stages_raw_form_data: Sequence[RawFormData],
    quick_setup_formspec_map: FormspecMap,
) -> Sequence[ValidationErrors] | None:
    stages_errors = []
    for stage_index in range(len(stages_raw_form_data)):
        errors = validate_stage_formspecs(
            stage_index=StageIndex(stage_index),
            stages_raw_formspecs=stages_raw_form_data[: stage_index + 1],
            quick_setup_formspec_map=quick_setup_formspec_map,
        )
        if errors.exist():
            stages_errors.append(errors)
    return stages_errors or None


def complete_quick_setup(
    action: QuickSetupAction,
    mode: QuickSetupActionMode,
    stages_raw_formspecs: Sequence[RawFormData],
    quick_setup_formspec_map: FormspecMap,
    object_id: str | None = None,
) -> QuickSetupSaveRedirect:
    return QuickSetupSaveRedirect(
        redirect_url=action.action(
            form_spec_parse(stages_raw_formspecs, quick_setup_formspec_map),
            mode,
            object_id,
        )
    )


class CompleteActionResult(BaseModel):
    all_stage_errors: Sequence[ValidationErrors] | None = None
    redirect_url: str | None = None
    background_job_exception: BackgroundJobException | None = None

    @classmethod
    def load_from_job_result(cls, job_id: str) -> "CompleteActionResult":
        work_dir = str(Path(BackgroundJobDefines.base_dir) / job_id)
        if not os.path.exists(work_dir):
            raise MKInternalError(None, _("Action result not found"))
        content = store.load_text_from_file(cls._file_path(work_dir))
        try:
            return cls.model_validate_json(content)
        except ValidationError as e:
            raise MKInternalError(
                None, f"Error reading action result with content: {content}"
            ) from e

    def save_to_file(self, work_dir: str) -> None:
        store.save_text_to_file(self._file_path(work_dir), self.model_dump_json())

    @staticmethod
    def _file_path(work_dir: str) -> str:
        return os.path.join(
            work_dir,
            "validation_and_action_result.json",
        )


def verify_custom_validators_and_complete_quick_setup(
    quick_setup: QuickSetup,
    action_id: ActionId,
    mode: QuickSetupActionMode,
    input_stages: Sequence[dict],
    form_spec_map: FormspecMap,
    object_id: str | None,
) -> CompleteActionResult:
    action = next((action for action in quick_setup.actions if action.id == action_id), None)
    if action is None:
        raise ValueError(f"Action with id {action_id} not found")
    stages_raw_formspecs = [RawFormData(stage["form_data"]) for stage in input_stages]
    errors = validate_custom_validators(
        quick_setup_id=quick_setup.id,
        custom_validators=action.custom_validators,
        stages_raw_formspecs=stages_raw_formspecs,
        quick_setup_formspec_map=form_spec_map,
    )
    if errors.exist():
        return CompleteActionResult(all_stage_errors=[errors])

    redirect_url = complete_quick_setup(
        action=action,
        mode=mode,
        stages_raw_formspecs=stages_raw_formspecs,
        quick_setup_formspec_map=form_spec_map,
        object_id=object_id,
    ).redirect_url
    return CompleteActionResult(redirect_url=redirect_url)


class QuickSetupActionBackgroundJob(BackgroundJob):
    housekeeping_max_age_sec = 1800
    housekeeping_max_count = 10

    job_prefix = "quick_setup_action"

    @classmethod
    def gui_title(cls) -> str:
        return _("Run Quick Setup Action")

    @classmethod
    def create_job_id(
        cls,
        quick_setup_id: str,
        job_uuid: str,
    ) -> str:
        return f"{cls.job_prefix}-{quick_setup_id.replace(':', '_')}-{job_uuid}"

    def __init__(
        self,
        job_uuid: str,
        quick_setup_id: QuickSetupId,
        action_id: ActionId,
        user_input_stages: Sequence[dict],
        mode: QuickSetupActionMode,
        object_id: str | None,
    ) -> None:
        self._quick_setup_id = quick_setup_id
        self._action_id = action_id
        self._user_input_stages = user_input_stages
        self._mode = mode
        self._object_id = object_id
        super().__init__(job_id=self.create_job_id(quick_setup_id, job_uuid))

    def run_quick_setup_stage(self, job_interface: BackgroundProcessInterface) -> None:
        job_interface.get_logger().debug("Running Quick setup action finally")
        with job_interface.gui_context():
            try:
                self._run_quick_setup_stage(job_interface)
            except Exception as e:
                job_interface.get_logger().debug(
                    "Exception raised while the Quick setup stage action: %s", e
                )
                exception_message = str(e)
                job_interface.send_exception(exception_message)
                CompleteActionResult(
                    background_job_exception=BackgroundJobException(
                        message=exception_message,
                        traceback=traceback.format_exc(),
                    )
                ).save_to_file(job_interface.get_work_dir())

    def _run_quick_setup_stage(self, job_interface: BackgroundProcessInterface) -> None:
        job_interface.send_progress_update(_("Starting Quick setup action..."))

        register_config_setups(quick_setup_registry)
        quick_setup = quick_setup_registry[self._quick_setup_id]
        action_result = verify_custom_validators_and_complete_quick_setup(
            quick_setup=quick_setup,
            action_id=self._action_id,
            mode=self._mode,
            input_stages=self._user_input_stages,
            form_spec_map=build_formspec_map_from_stages([stage() for stage in quick_setup.stages]),
            object_id=self._object_id,
        )

        job_interface.send_progress_update(_("Saving the result..."))
        action_result.save_to_file(job_interface.get_work_dir())
        job_interface.send_result_message("Job finished.")


def start_quick_setup_job(
    quick_setup: QuickSetup,
    action_id: ActionId,
    mode: QuickSetupActionMode,
    user_input_stages: Sequence[dict],
    object_id: str | None,
) -> str:
    job_uuid = str(uuid.uuid4())
    job = QuickSetupActionBackgroundJob(
        job_uuid=job_uuid,
        quick_setup_id=quick_setup.id,
        action_id=action_id,
        user_input_stages=user_input_stages,
        mode=mode,
        object_id=object_id,
    )

    job_start = job.start(
        job.run_quick_setup_stage,
        InitialStatusArgs(
            title=_("Running Quick setup %s action %s") % (quick_setup.id, action_id),
            user=str(user.id) if user.id else None,
        ),
    )
    if job_start.is_error():
        raise MKUserError(None, str(job_start.error))

    return job.get_job_id()

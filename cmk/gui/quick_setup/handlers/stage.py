#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"

import os
import traceback
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, override

from pydantic import BaseModel, ValidationError

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _
from cmk.ccc.site import SiteId
from cmk.gui.background_job.job import (
    BackgroundJob,
    BackgroundJobDefines,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.config import Config
from cmk.gui.exceptions import MKInternalError, MKUserError
from cmk.gui.form_specs import get_visitor, RawFrontendData, VisitorOptions
from cmk.gui.http import Request
from cmk.gui.i18n import localize
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.quick_setup.handlers.utils import (
    Action,
    BackgroundJobException,
    Button,
    form_spec_parse,
    get_stage_components_from_widget,
    InfoLogger,
    JobBasedProgressLogger,
    LOAD_WAIT_LABEL,
    MKJobNotFoundException,
    NEXT_BUTTON_ARIA_LABEL,
    NEXT_BUTTON_LABEL,
    PREV_BUTTON_ARIA_LABEL,
    QuickSetupValidationError,
    stage_applicability_and_form_data,
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
    ProgressLogger,
    QuickSetup,
    QuickSetupContext,
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
from cmk.gui.type_defs import CustomHostAttrSpec
from cmk.gui.utils.roles import UserPermissions, UserPermissionSerializableConfig
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    do_remote_automation,
    MKAutomationException,
)
from cmk.gui.watolib.hosts_and_folders import FolderTree, HostsAndFoldersConfig
from cmk.livestatus_client import SiteConfigurations
from cmk.ruleset_matcher.tags import TagConfig, TagConfigSpec
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.utils.automation_config import RemoteAutomationConfig


class InvalidStageException(MKGeneralException):
    pass


# TODO: This dataclass is already defined in
# cmk.gui.form_specs.autogen_type_defs.vue_formspec_components
# but can't be imported here. Once we move this module, we can remove this
# and use the one from the other module.


def _stage_validate_all_form_spec_keys_existing(
    current_stage_form_data: RawFormData,
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> GeneralStageErrors:
    return [
        f"Formspec id '{form_spec_id}' not found"
        for form_spec_id in current_stage_form_data
        if form_spec_id not in expected_formspecs_map
    ]


def _form_spec_validate(
    current_stage_form_data: RawFormData,
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> ValidationErrorMap:
    return {
        form_spec_id: [QuickSetupValidationError(**asdict(error)) for error in errors]
        for form_spec_id, form_data in current_stage_form_data.items()
        if (
            errors := get_visitor(
                expected_formspecs_map[form_spec_id],
                VisitorOptions(migrate_values=True, mask_values=False),
            ).validate(RawFrontendData(form_data))
        )
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
    progress_logger: ProgressLogger,
    ctx: QuickSetupContext,
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

        progress_logger:
            The logger to log progress messages to.
    """
    errors = ValidationErrors(stage_index=stage_index)
    custom_validators = matching_stage_action(
        stages[stage_index], stage_action_id
    ).custom_validators
    errors.stage_errors.extend(
        validate_custom_validators(
            quick_setup_id=quick_setup.id,
            custom_validators=custom_validators,
            stages_raw_formspecs=stages_raw_formspecs,
            quick_setup_formspec_map=quick_setup_formspec_map,
            progress_logger=progress_logger,
            ctx=ctx,
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
    progress_logger: ProgressLogger,
    ctx: QuickSetupContext,
) -> Sequence[Widget]:
    parsed_formspec = form_spec_parse(stages_raw_formspecs, quick_setup_formspec_map)
    recap_widgets: list[Widget] = []
    for recap_callable in matching_stage_action(stages[stage_index], stage_action_id).recap:
        recap_widgets.extend(
            recap_callable(
                quick_setup_id,
                stage_index,
                parsed_formspec,
                progress_logger,
                ctx,
            )
        )
    return recap_widgets


class StageActionResult(BaseModel, frozen=False):
    quick_setup_id: QuickSetupId
    stage_index: StageIndex
    action_id: ActionId
    validation_errors: ValidationErrors | None = None
    # TODO: This should be a list of widgets using only Sequence[Widget] will remove all fields
    #  when the data is returned (this is a temporary fix)
    stage_recap: Sequence[Any] = field(default_factory=list)
    stage_applicability: Sequence[bool] = field(default_factory=list)
    background_job_exception: BackgroundJobException | None = None

    @classmethod
    def load_from_job_result(cls, job_id: str) -> StageActionResult:
        work_dir = Path(BackgroundJobDefines.base_dir) / job_id
        if not os.path.exists(work_dir):
            raise MKJobNotFoundException(None, _("Stage action result not found"))
        content = store.load_text_from_file(cls._file_path(work_dir))
        try:
            return cls.model_validate_json(content)
        except ValidationError as e:
            raise MKInternalError(
                None, f"Error reading stage action result with content: {content}"
            ) from e

    def save_to_file(self, work_dir: Path) -> None:
        store.save_text_to_file(self._file_path(work_dir), self.model_dump_json())

    @staticmethod
    def _file_path(work_dir: Path) -> Path:
        return work_dir / "validation_and_recap_result.json"


def verify_custom_validators_and_recap_stage(
    *,
    quick_setup: QuickSetup,
    stage_index: StageIndex,
    stage_action_id: ActionId,
    input_stages: Sequence[dict],
    form_spec_map: FormspecMap,
    built_stages: Sequence[QuickSetupStage],
    progress_logger: ProgressLogger | None,
    ctx: QuickSetupContext,
) -> StageActionResult:
    if progress_logger is None:
        progress_logger = InfoLogger()

    stage_applicability, stages_raw_formspecs = stage_applicability_and_form_data(
        quick_setup.stages,
        [RawFormData(stage["form_data"]) for stage in input_stages],
        form_spec_map,
    )
    response = StageActionResult(
        quick_setup_id=quick_setup.id,
        stage_index=stage_index,
        action_id=stage_action_id,
        stage_applicability=stage_applicability,
    )
    if (
        errors := verify_stage_custom_validators(
            quick_setup=quick_setup,
            stages_raw_formspecs=stages_raw_formspecs,
            stage_index=stage_index,
            stage_action_id=stage_action_id,
            stages=built_stages,
            quick_setup_formspec_map=form_spec_map,
            progress_logger=progress_logger,
            ctx=ctx,
        )
    ) is not None:
        response.validation_errors = errors
        return response

    response.stage_recap = recap_stage(
        quick_setup_id=quick_setup.id,
        stage_index=stage_index,
        stages=built_stages,
        stage_action_id=stage_action_id,
        stages_raw_formspecs=stages_raw_formspecs,
        quick_setup_formspec_map=form_spec_map,
        progress_logger=progress_logger,
        ctx=ctx,
    )
    return response


class QuickSetupStageActionBackgroundJob(BackgroundJob):
    housekeeping_max_age_sec = 1800
    housekeeping_max_count = 10

    job_prefix = "quick_setup_stage_action"

    @classmethod
    @override
    def gui_title(cls) -> str:
        return _("Run Quick Setup stage action")

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
        language: str,
    ) -> None:
        self._quick_setup_id = quick_setup_id
        self._action_id = action_id
        self._stage_index = stage_index
        self._user_input_stages = user_input_stages
        # TODO (localization): localization is currently unavailable on VueJS and therefore needs
        #  to be done inside the Background job which is not ideal. This should be removed here (as
        #  as well as the call instances) once the localization mechanism is available on the VueJS
        #  side. This approach saves the Quick setup progress steps in the translated language which
        #  is also not ideal
        self._language = language
        super().__init__(job_id=self.create_job_id(quick_setup_id, stage_index, job_uuid))

    def run_quick_setup_stage_action(
        self,
        job_interface: BackgroundProcessInterface,
        user_permission_config: UserPermissionSerializableConfig,
        *,
        site_configs: SiteConfigurations,
        debug: bool,
        use_git: bool,
        pprint_value: bool,
        wato_hide_folders_without_read_permissions: bool,
        wato_host_attrs: Sequence[CustomHostAttrSpec],
        tags: TagConfigSpec,
    ) -> None:
        job_interface.get_logger().debug("Running Quick setup stage action finally")
        with job_interface.gui_context(
            UserPermissions.from_serialized_config(user_permission_config, permission_registry)
        ):
            localize(self._language)
            try:
                self._run_quick_setup_stage_action(
                    job_interface,
                    ctx=QuickSetupContext(
                        tree=FolderTree(
                            config=HostsAndFoldersConfig(
                                wato_hide_folders_without_read_permissions=wato_hide_folders_without_read_permissions,
                                wato_host_attrs=wato_host_attrs,
                                tags=TagConfig.from_config(tags),
                                sites=site_configs,
                            )
                        ),
                        site_configs=site_configs,
                        debug=debug,
                        use_git=use_git,
                        pprint_value=pprint_value,
                    ),
                )
            except Exception as e:
                job_interface.get_logger().debug(
                    "Exception raised while the Quick setup stage action: %(error)s", {"error": e}
                )
                exception_message = str(e)
                job_interface.send_exception(exception_message)
                StageActionResult(
                    quick_setup_id=self._quick_setup_id,
                    stage_index=self._stage_index,
                    action_id=self._action_id,
                    background_job_exception=BackgroundJobException(
                        message=exception_message, traceback=traceback.format_exc()
                    ),
                ).save_to_file(Path(job_interface.get_work_dir()))

    def _run_quick_setup_stage_action(
        self, job_interface: BackgroundProcessInterface, *, ctx: QuickSetupContext
    ) -> None:
        job_interface.send_progress_update(_("Starting Quick stage action..."))

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
            progress_logger=JobBasedProgressLogger(job_interface),
            ctx=ctx,
        )

        job_interface.send_progress_update(_("Saving the result..."))
        action_result.save_to_file(Path(job_interface.get_work_dir()))
        job_interface.send_result_message("Job finished.")


def start_quick_setup_stage_job(
    quick_setup_id: QuickSetupId,
    action_id: ActionId,
    stage_index: StageIndex,
    user_input_stages: Sequence[dict],
    language: str,
    user_permission_config: UserPermissionSerializableConfig,
    job_uuid: str | None,
    *,
    site_configs: SiteConfigurations,
    debug: bool,
    use_git: bool,
    pprint_value: bool,
    wato_hide_folders_without_read_permissions: bool,
    wato_host_attrs: Sequence[CustomHostAttrSpec],
    tags: TagConfigSpec,
) -> str:
    if job_uuid is None:
        job_uuid = str(uuid.uuid4())
    job = QuickSetupStageActionBackgroundJob(
        job_uuid=job_uuid,
        quick_setup_id=quick_setup_id,
        action_id=action_id,
        stage_index=stage_index,
        user_input_stages=user_input_stages,
        language=language,
    )

    job_start = job.start(
        JobTarget(
            callable=quick_setup_stage_action_job_entry_point,
            args=QuickSetupStageActionJobArgs(
                job_uuid=job_uuid,
                quick_setup_id=quick_setup_id,
                action_id=action_id,
                stage_index=stage_index,
                user_input_stages=user_input_stages,
                language=language,
                user_permission_config=user_permission_config,
                site_configs=site_configs,
                debug=debug,
                use_git=use_git,
                pprint_value=pprint_value,
                wato_hide_folders_without_read_permissions=wato_hide_folders_without_read_permissions,
                wato_host_attrs=wato_host_attrs,
                tags=tags,
            ),
        ),
        InitialStatusArgs(
            title=_(
                "Running Quick Setup %(quick_setup_id)s stage %(stage_index)s action %(action_id)s"
            )
            % {
                "quick_setup_id": quick_setup_id,
                "stage_index": stage_index,
                "action_id": action_id,
            },
            user=str(user.id) if user.id else None,
        ),
    )
    if job_start.is_error():
        raise MKUserError(None, str(job_start.error))

    return job.get_job_id()


class QuickSetupStageActionRemoteArgs(BaseModel, frozen=True):
    """What a central site sends to a remote site to start a stage action there"""

    job_uuid: str
    quick_setup_id: QuickSetupId
    action_id: ActionId
    stage_index: StageIndex
    user_input_stages: Sequence[dict]
    language: str
    user_permission_config: UserPermissionSerializableConfig


class QuickSetupStageActionJobArgs(QuickSetupStageActionRemoteArgs, frozen=True):
    site_configs: SiteConfigurations
    debug: bool
    use_git: bool
    pprint_value: bool
    wato_hide_folders_without_read_permissions: bool
    wato_host_attrs: Sequence[CustomHostAttrSpec]
    tags: TagConfigSpec


def quick_setup_stage_action_job_entry_point(
    job_interface: BackgroundProcessInterface, args: QuickSetupStageActionJobArgs
) -> None:
    QuickSetupStageActionBackgroundJob(
        job_uuid=args.job_uuid,
        quick_setup_id=args.quick_setup_id,
        action_id=args.action_id,
        stage_index=args.stage_index,
        user_input_stages=args.user_input_stages,
        language=args.language,
    ).run_quick_setup_stage_action(
        job_interface,
        user_permission_config=args.user_permission_config,
        site_configs=args.site_configs,
        debug=args.debug,
        use_git=args.use_git,
        pprint_value=args.pprint_value,
        wato_hide_folders_without_read_permissions=args.wato_hide_folders_without_read_permissions,
        wato_host_attrs=args.wato_host_attrs,
        tags=args.tags,
    )


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


def start_quick_setup_stage_action_job_on_remote(
    site_id: SiteId,
    automation_config: RemoteAutomationConfig,
    user_permission_config: UserPermissionSerializableConfig,
    quick_setup_id: QuickSetupId,
    action_id: ActionId,
    stage_index: StageIndex,
    user_input_stages: Sequence[dict],
    language: str,
    *,
    debug: bool,
) -> str:
    job_uuid = str(uuid.uuid4())
    args = QuickSetupStageActionRemoteArgs(
        job_uuid=job_uuid,
        quick_setup_id=quick_setup_id,
        action_id=action_id,
        stage_index=stage_index,
        user_input_stages=user_input_stages,
        language=language,
        user_permission_config=user_permission_config,
    )
    try:
        job_id = str(
            do_remote_automation(
                automation_config,
                "start-quick-setup-stage-action",
                [
                    ("args", args.model_dump_json()),
                ],
                debug=debug,
            )
        )
    except (MKAutomationException, MKUserError) as e:
        raise MKUserError(
            None,
            _("Failed to start the stage action on remote site %(site_id)s: %(e)s")
            % {"site_id": site_id, "e": e},
        ) from e
    return job_id


class AutomationQuickSetupStageAction(AutomationCommand[QuickSetupStageActionJobArgs]):
    """Start a Quick Setup stage action in the background on a remote site

    The stage action runs with the configuration of the remote site, not the one of the central
    site that asked for it."""

    @override
    def command_name(self) -> str:
        return "start-quick-setup-stage-action"

    @override
    def get_request(self, config: Config, request: Request) -> QuickSetupStageActionJobArgs:
        api_request = request.get_request()
        # When called from a 2.4 central site, the field is missing. Use the local config.
        if "user_permission_config" not in api_request:
            api_request["user_permission_config"] = (
                UserPermissionSerializableConfig.from_global_config(config)
            )
        remote_args = QuickSetupStageActionRemoteArgs.model_validate_json(api_request["args"])
        return QuickSetupStageActionJobArgs(
            **dict(remote_args),
            site_configs=config.sites,
            debug=config.debug,
            use_git=config.wato_use_git,
            pprint_value=config.wato_pprint_config,
            wato_hide_folders_without_read_permissions=config.wato_hide_folders_without_read_permissions,
            wato_host_attrs=config.wato_host_attrs,
            tags=config.tags.get_dict_format(),
        )

    @override
    def execute(self, api_request: QuickSetupStageActionJobArgs) -> str:
        return start_quick_setup_stage_job(
            quick_setup_id=api_request.quick_setup_id,
            action_id=api_request.action_id,
            stage_index=api_request.stage_index,
            user_input_stages=api_request.user_input_stages,
            job_uuid=api_request.job_uuid,
            language=api_request.language,
            user_permission_config=api_request.user_permission_config,
            site_configs=api_request.site_configs,
            debug=api_request.debug,
            use_git=api_request.use_git,
            pprint_value=api_request.pprint_value,
            wato_hide_folders_without_read_permissions=api_request.wato_hide_folders_without_read_permissions,
            wato_host_attrs=api_request.wato_host_attrs,
            tags=api_request.tags,
        )


class AutomationQuickSetupStageActionResult(AutomationCommand[str]):
    """Fetch the result of a Quick Setup stage action from a remote site"""

    @override
    def command_name(self) -> str:
        return "fetch-quick-setup-stage-action-result"

    @override
    def get_request(self, config: Config, request: Request) -> str:
        job_id = request.get_request()["job_id"]
        assert isinstance(job_id, str)
        return job_id

    @override
    def execute(self, api_request: str) -> str:
        return StageActionResult.load_from_job_result(api_request).model_dump_json()

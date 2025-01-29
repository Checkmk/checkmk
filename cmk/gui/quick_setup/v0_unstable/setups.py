#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ActionId,
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, Widget

from cmk.rulesets.v1.form_specs import FormSpec


class QuickSetupActionMode(StrEnum):
    SAVE = "save"
    EDIT = "edit"


FormspecMap = Mapping[FormSpecId, FormSpec]
# TODO: Validator should be refactored so during complete action, overlapping validations can be
#  skipped
CallableValidator = Callable[[QuickSetupId, ParsedFormData], GeneralStageErrors]
CallableRecap = Callable[[QuickSetupId, StageIndex, ParsedFormData], Sequence[Widget]]
CallableAction = Callable[[ParsedFormData, QuickSetupActionMode, str | None], str]
WidgetConfigurator = Callable[[], Sequence[Widget]]


@dataclass(frozen=True)
class QuickSetupStageAction:
    """Data class representing an action that can be triggered in a quick setup stage when
    proceeding to the next stage.

        Notes:
            * An action is triggered when the user clicks the action button.
            * An successful action conditions that all validators (custom and built-in) pass.
            * Passing of all validations will result in a summarized view of the stage data defined
            by the recap callables.

        Attributes:
            id:
                The unique identifier of the action. Ids only need to be unique within the stage.

            custom_validators:
                A list of custom validators that are executed when the action is triggered. Custom
                validators are executed alongside the formspec validation

            recap:
                A list of recap callables with each callable returning a list of widgets that are
                displayed in the recap section of the stage. The recap section conditions that all
                validators have passed.

            next_button_label:
                The label of the action button. If not set, the default label is used.

            load_wait_label:
                The label of the loading spinner. If not set, the default label is used.

            run_in_background:
                A flag indicating if the action should be executed in the background. This should
                be used for actions that CAN take a long time to complete. This is
                necessary as the interface will run into a Gateway Timeout error after 120 seconds
    """

    id: ActionId
    custom_validators: Iterable[CallableValidator]
    recap: Iterable[CallableRecap]
    next_button_label: str | None = None
    load_wait_label: str | None = None
    run_in_background: bool = False


@dataclass(frozen=True)
class QuickSetupStage:
    """Quick setup stage definition

    Attributes:
        title:
            The title of the stage

        configure_components:
            A callable that returns a sequence of widgets that are displayed in the stage body
            (only visible if the stage is on focus)

        actions:
            A sequence of mutually exclusive stage actions that can be triggered in the stage

        sub_title:
            The sub-title description of the stage

        prev_button_label:
            The label of the previous button. If not set, the default label is used.
    """

    title: str
    configure_components: WidgetConfigurator | Sequence[Widget]
    actions: Sequence[QuickSetupStageAction]
    sub_title: str | None = None
    prev_button_label: str | None = None


@dataclass(frozen=True)
class QuickSetupAction:
    """Dataclass representing an action that can be triggered at the end of the Quick setup flow.

    Attributes:
        id:
            The unique identifier of the action
        label:
            The label of the action button
        action:
            The callable that is executed when the action is triggered
        custom_validators:
            A list of custom validators that are executed before the action is executed.
            Prior to the custom validators, the formspecs of each stage are validated (again
            if the user is in the 'guided' mode).


            The individual stage custom validators are not executed. This is due to the fact
            that some stage validations overlap in context with each other
            (e.g. check key connection and then check the entire configuration).

            Therefore, relevant custom validators should be included again here (especially
            if the 'overview' mode is enabled)
        run_in_background:
            A flag indicating if the action should be executed in the background. This should
            be used for actions that CAN take a long time to complete. This is
            necessary as the interface will run into a Gateway Timeout error after 120 seconds
    """

    id: ActionId
    label: str
    action: CallableAction
    custom_validators: Iterable[CallableValidator] = ()
    run_in_background: bool = False


@dataclass(frozen=True)
class QuickSetup:
    title: str
    id: QuickSetupId
    stages: Sequence[Callable[[], QuickSetupStage]]
    actions: Sequence[QuickSetupAction]
    load_data: Callable[[str], ParsedFormData | None] = lambda _: None

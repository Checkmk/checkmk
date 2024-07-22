#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Iterable, MutableMapping, MutableSequence, Sequence
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, NewType

from cmk.utils.quick_setup.widgets import FormSpecId, Widget

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.plugin_registry import Registry
from cmk.rulesets.v1.form_specs import FormSpec

StageId = NewType("StageId", int)
QuickSetupId = NewType("QuickSetupId", str)
FormData = NewType("FormData", Mapping[FormSpecId, object])


# TODO: This dataclass is already defined in
# cmk.gui.form_specs.vue.autogen_type_defs.vue_formspec_components
# but can't be imported here. Once we move this module, we can remove this
# and use the one from the other module.
@dataclass
class QuickSetupValidationError:
    message: str
    invalid_value: Any
    location: Sequence[str] = field(default_factory=list)


GeneralStageErrors = MutableSequence[str]
ValidationErrorMap = MutableMapping[FormSpecId, MutableSequence[QuickSetupValidationError]]
CallableValidator = Callable[
    [Sequence[FormData], Mapping[FormSpecId, FormSpec]],
    tuple[ValidationErrorMap, GeneralStageErrors],
]


@dataclass
class StageOverview:
    stage_id: StageId
    title: str
    sub_title: str | None


@dataclass
class Errors:
    formspec_errors: ValidationErrorMap = field(default_factory=dict)
    stage_errors: GeneralStageErrors = field(default_factory=list)


@dataclass
class Stage:
    stage_id: StageId
    components: Sequence[dict]
    button_txt: str | None
    errors: Errors | None = None
    stage_recap: Sequence[Widget] = field(default_factory=list)


@dataclass
class QuickSetupStage:
    stage_id: StageId
    title: str
    configure_components: Sequence[Widget]
    validators: Iterable[CallableValidator]
    recap: Iterable[Callable[[Sequence[FormData]], Sequence[Widget]]]
    button_txt: str
    sub_title: str | None = None

    def stage_overview(self) -> StageOverview:
        return StageOverview(
            stage_id=self.stage_id,
            title=self.title,
            sub_title=self.sub_title,
        )


@dataclass
class QuickSetupOverview:
    quick_setup_id: QuickSetupId
    overviews: list[StageOverview]
    stage: Stage


@dataclass
class IncomingStage:  # Request
    stage_id: StageId
    form_data: FormData


class InvalidStageException(MKGeneralException):
    pass


@dataclass
class QuickSetupSaveRedirect:
    redirect_url: str | None = None


@dataclass
class QuickSetup:
    title: str
    id: QuickSetupId
    stages: Sequence[QuickSetupStage]
    save_action: Callable[[Sequence[IncomingStage]], str] | None = None

    def get_stage_with_id(self, stage_id: StageId) -> QuickSetupStage:
        for stage in self.stages:
            if stage.stage_id == stage_id:
                return stage
        raise InvalidStageException(f"The stage id '{stage_id}' does not exist.")


class QuickSetupNotFoundException(MKGeneralException):
    pass


class QuickSetupRegistry(Registry[QuickSetup]):
    def plugin_name(self, instance: QuickSetup) -> str:
        return str(instance.id)


quick_setup_registry = QuickSetupRegistry()

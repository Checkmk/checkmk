#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Callable, Mapping, NewType

from cmk.utils.plugin_registry import Registry
from cmk.utils.quick_setup.widgets import FormSpecId, Widget

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import FormSpec

StageId = NewType("StageId", int)
QuickSetupId = NewType("QuickSetupId", str)


@dataclass
class StageOverview:
    stage_id: StageId
    title: str
    sub_title: str | None


@dataclass
class Stage:
    stage_id: StageId
    components: Sequence[dict]
    validation_errors: Sequence[str] = field(default_factory=list)
    stage_summary: Sequence[str] = field(default_factory=list)


@dataclass
class QuickSetupStage:
    stage_id: StageId
    title: str
    configure_components: Sequence[Widget]
    validators: Iterable[Callable[[Sequence[dict], Mapping[FormSpecId, FormSpec]], Sequence[str]]]
    recap: Iterable[Callable[[Sequence[dict]], Sequence[Widget]]]
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
    form_data: dict[FormSpecId, object]


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

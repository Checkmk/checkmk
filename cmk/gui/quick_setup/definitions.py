#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict, dataclass, field
from typing import Mapping, TypedDict

from cmk.utils.exceptions import MKGeneralException

from cmk.gui.quick_setup.widgets import Widget

StageId = int
QuickSetupId = str


@dataclass
class StageOverview:
    stage_id: StageId
    title: str
    sub_title: str | None


@dataclass
class Stage(TypedDict):
    stage_id: StageId
    components: list[dict]


@dataclass
class QuickSetupStage:
    stage_id: StageId
    title: str
    components: list[Widget] = field(default_factory=list)
    sub_title: str | None = None

    def stage_overview(self) -> StageOverview:
        return StageOverview(
            stage_id=self.stage_id,
            title=self.title,
            sub_title=self.sub_title,
        )

    def stage(self) -> Stage:
        return Stage(
            stage_id=self.stage_id,
            components=[_serialize_widget(widget) for widget in self.components],
        )


def _serialize_widget(widget: Widget) -> dict:
    return asdict(widget)


@dataclass
class QuickSetupOverview:
    quick_setup_id: QuickSetupId
    overviews: list[StageOverview]
    stage: Stage


@dataclass
class QuickSetup:
    id: QuickSetupId
    stages: Mapping[StageId, QuickSetupStage]

    def wizard_overview(self) -> QuickSetupOverview:
        return QuickSetupOverview(
            quick_setup_id=self.id,
            overviews=[stage.stage_overview() for stage in self.stages.values()],
            stage=self.stages[1].stage(),
        )


class QuickSetupNotFoundException(MKGeneralException):
    pass


class QuickSetupRegistry:
    def __init__(self):
        self.quick_setups: dict[QuickSetupId, QuickSetup] = {}

    def add_quick_setup(self, quick_setup: QuickSetup) -> None:
        self.quick_setups[quick_setup.id] = quick_setup

    def get(self, quick_setup_id: QuickSetupId) -> QuickSetup:
        if quick_setup_id not in self.quick_setups:
            raise QuickSetupNotFoundException(
                f"The Quick setup with id '{quick_setup_id}' does not exist."
            )
        return self.quick_setups[quick_setup_id]


quick_setup_registry = QuickSetupRegistry()

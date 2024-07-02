#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import cast, NewType

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.type_defs import DataOrigin
from cmk.gui.quick_setup.widgets import FormSpecWrapper, Widget

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
    components: list[dict]
    validation_errors: list[str] = field(default_factory=list)


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


def get_stage_components_for_the_frontend(quick_setup_stage: QuickSetupStage) -> list[dict]:
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
            components.append(asdict(widget))
    return components


@dataclass
class QuickSetupOverview:
    quick_setup_id: QuickSetupId
    overviews: list[StageOverview]
    stage: Stage


@dataclass
class QuickSetup:
    id: QuickSetupId
    stages: Sequence[QuickSetupStage]

    def overview(self) -> QuickSetupOverview:
        for stage in self.stages:
            if stage.stage_id == StageId(1):
                return QuickSetupOverview(
                    quick_setup_id=self.id,
                    overviews=[stage.stage_overview() for stage in self.stages],
                    stage=Stage(
                        stage_id=stage.stage_id,
                        components=get_stage_components_for_the_frontend(stage),
                    ),
                )
        raise MKGeneralException("The first stage is missing.")


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

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from cmk.gui.quick_setup.v0_unstable.definitions import (
    CallableRecap,
    CallableValidator,
    IncomingStage,
    InvalidStageException,
    StageOverview,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import QuickSetupId, StageId
from cmk.gui.quick_setup.v0_unstable.widgets import Widget


@dataclass(frozen=True)
class QuickSetupStage:
    stage_id: StageId
    title: str
    configure_components: Sequence[Widget]
    validators: Iterable[CallableValidator]
    recap: Iterable[CallableRecap]
    button_txt: str
    sub_title: str | None = None

    def stage_overview(self) -> StageOverview:
        return StageOverview(
            stage_id=self.stage_id,
            title=self.title,
            sub_title=self.sub_title,
        )


@dataclass(frozen=True)
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

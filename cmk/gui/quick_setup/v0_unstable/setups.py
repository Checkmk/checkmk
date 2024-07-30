#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
    StageId,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, Widget

from cmk.rulesets.v1.form_specs import FormSpec

CallableValidator = Callable[[ParsedFormData, Mapping[FormSpecId, FormSpec]], GeneralStageErrors]
CallableRecap = Callable[
    [Sequence[ParsedFormData], Mapping[FormSpecId, FormSpec]],
    Sequence[Widget],
]
CallableSaveAction = Callable[[ParsedFormData], str]


@dataclass(frozen=True)
class QuickSetupStage:
    stage_id: StageId
    title: str
    configure_components: Sequence[Widget]
    validators: Iterable[CallableValidator]
    recap: Iterable[CallableRecap]
    button_txt: str
    sub_title: str | None = None


@dataclass(frozen=True)
class QuickSetup:
    title: str
    id: QuickSetupId
    stages: Sequence[QuickSetupStage]
    button_complete_label: str
    save_action: CallableSaveAction | None = None

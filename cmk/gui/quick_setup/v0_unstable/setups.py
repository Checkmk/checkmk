#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, Widget

from cmk.rulesets.v1.form_specs import FormSpec

CallableValidator = Callable[[ParsedFormData, Mapping[FormSpecId, FormSpec]], GeneralStageErrors]
CallableRecap = Callable[
    [Sequence[ParsedFormData], Mapping[FormSpecId, FormSpec]],
    Sequence[Widget],
]
CallableSaveAction = Callable[[ParsedFormData], str]
WidgetConfigurator = Callable[[], Sequence[Widget]]


@dataclass(frozen=True)
class QuickSetupStage:
    title: str
    configure_components: WidgetConfigurator | Sequence[Widget]
    custom_validators: Iterable[CallableValidator]
    recap: Iterable[CallableRecap]
    button_label: str
    sub_title: str | None = None


@dataclass(frozen=True)
class QuickSetup:
    title: str
    id: QuickSetupId
    stages: Sequence[QuickSetupStage]
    button_complete_label: str
    save_action: CallableSaveAction | None = None

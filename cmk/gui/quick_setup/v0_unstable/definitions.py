#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import MutableMapping, MutableSequence, Sequence
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, NewType

from cmk.gui.quick_setup.v0_unstable.type_defs import QuickSetupId, StageId
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, Widget

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import FormSpec

RawFormData = NewType("RawFormData", Mapping[FormSpecId, object])
ParsedFormData = Mapping[FormSpecId, Any]


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
CallableValidator = Callable[[ParsedFormData, Mapping[FormSpecId, FormSpec]], GeneralStageErrors]
CallableRecap = Callable[
    [Sequence[ParsedFormData], Mapping[FormSpecId, FormSpec]],
    Sequence[Widget],
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
class QuickSetupOverview:
    quick_setup_id: QuickSetupId
    overviews: list[StageOverview]
    stage: Stage


@dataclass
class IncomingStage:  # Request
    stage_id: StageId
    form_data: RawFormData


class InvalidStageException(MKGeneralException):
    pass


@dataclass
class QuickSetupSaveRedirect:
    redirect_url: str | None = None


class QuickSetupNotFoundException(MKGeneralException):
    pass


UniqueFormSpecIDStr = "formspec_unique_id"
UniqueBundleIDStr = "bundle_id"

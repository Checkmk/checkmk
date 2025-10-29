#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, override

from cmk.gui.form_specs.unstable.binary_condition_choices import (
    BinaryConditionChoices as BinaryConditionChoicesAPI,
)
from cmk.gui.i18n import _
from cmk.shared_typing.vue_formspec_components import (
    BinaryConditionChoices as BinaryConditionChoices,
)
from cmk.shared_typing.vue_formspec_components import (
    BinaryConditionChoicesGroup as BinaryConditionChoicesGroup,
)
from cmk.shared_typing.vue_formspec_components import (
    BinaryConditionChoicesItem as BinaryConditionChoicesItem,
)
from cmk.shared_typing.vue_formspec_components import (
    BinaryConditionChoicesOperator as BinaryConditionChoicesOperator,
)
from cmk.shared_typing.vue_formspec_components import (
    BinaryConditionChoicesValue as BinaryConditionChoicesValue,
)
from cmk.shared_typing.vue_formspec_components import (
    ValidationMessage as ValidationMessage,
)

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, IncomingData, InvalidValue, RawFrontendData
from ._utils import (
    compute_validation_errors,
    compute_validators,
    get_title_and_help,
    localize,
)
from .validators import build_vue_validators

type _TFallbackModel = BinaryConditionChoicesValue


def _parse_operator(raw_value: object) -> BinaryConditionChoicesOperator:
    if not isinstance(raw_value, str):
        raise TypeError(raw_value)
    match raw_value:
        case "and":
            return BinaryConditionChoicesOperator.and_
        case "or":
            return BinaryConditionChoicesOperator.or_
        case "not":
            return BinaryConditionChoicesOperator.not_
        case _:
            raise ValueError(raw_value)


def _parse_frontend(
    raw_value: object,
) -> BinaryConditionChoicesValue | InvalidValue[_TFallbackModel]:
    if not isinstance(raw_value, list):
        raise TypeError(raw_value)
    try:
        return [
            BinaryConditionChoicesGroup(
                operator=_parse_operator(raw_group["operator"]),
                label_group=[
                    BinaryConditionChoicesItem(
                        operator=_parse_operator(raw_item["operator"]),
                        label=raw_item["label"],
                    )
                    for raw_item in raw_group["label_group"]
                ],
            )
            for raw_group in raw_value
            if raw_group["label_group"]
        ]
    except (TypeError, ValueError):
        return InvalidValue(fallback_value=[], reason=_("Invalid data"))


def _parse_disk(
    raw_value: object,
) -> BinaryConditionChoicesValue | InvalidValue[_TFallbackModel]:
    if not isinstance(raw_value, list):
        return InvalidValue(fallback_value=[], reason=_("Invalid data"))
    try:
        return [
            BinaryConditionChoicesGroup(
                operator=_parse_operator(raw_group_operator),
                label_group=[
                    BinaryConditionChoicesItem(
                        operator=_parse_operator(raw_operator),
                        label=raw_label,
                    )
                    for raw_operator, raw_label in raw_label_group
                ],
            )
            for raw_group_operator, raw_label_group in raw_value
        ]
    except (TypeError, ValueError):
        return InvalidValue(fallback_value=[], reason=_("Invalid data"))


class BinaryConditionChoicesVisitor(
    FormSpecVisitor[BinaryConditionChoicesAPI, BinaryConditionChoicesValue, _TFallbackModel]
):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> BinaryConditionChoicesValue | InvalidValue[_TFallbackModel]:
        if isinstance(raw_value, DefaultValue):
            return InvalidValue(fallback_value=[], reason=_("No default values can be set."))

        if isinstance(raw_value, RawFrontendData):
            return _parse_frontend(raw_value.value)

        return _parse_disk(raw_value.value)

    @override
    def _to_vue(
        self,
        parsed_value: BinaryConditionChoicesValue | InvalidValue[_TFallbackModel],
    ) -> tuple[BinaryConditionChoices, object]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            BinaryConditionChoices(
                title=title,
                help=help_text,
                label=localize(self.form_spec.label),
                conditions=self.form_spec.get_conditions(),
                validators=build_vue_validators(self.form_spec.custom_validate or []),
            ),
            [] if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    @override
    def _validate(self, parsed_value: BinaryConditionChoicesValue) -> list[ValidationMessage]:
        vue_value = [] if isinstance(parsed_value, InvalidValue) else parsed_value
        return compute_validation_errors(
            compute_validators(self.form_spec), lambda: vue_value, vue_value
        )

    @override
    def _to_disk(
        self, parsed_value: BinaryConditionChoicesValue
    ) -> Sequence[
        tuple[Literal["and", "or", "not"], Sequence[tuple[Literal["and", "or", "not"], str]]]
    ]:
        return [
            (r.operator.value, [(gr.operator.value, gr.label) for gr in r.label_group])
            for r in parsed_value
        ]

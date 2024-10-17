#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from typing import Sequence, TypeVar

from cmk.gui.form_specs.private.labels import Labels
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import translate_to_current_language

from cmk.rulesets.v1 import Title

from ._base import FormSpecVisitor
from ._type_defs import EMPTY_VALUE, EmptyValue
from ._utils import (
    compute_validation_errors,
    create_validation_error,
    get_title_and_help,
)

T = TypeVar("T")


class LabelsVisitor(FormSpecVisitor[Labels, Mapping[str, str]]):
    def _parse_value(self, raw_value: object) -> Mapping[str, str] | EmptyValue:
        if not isinstance(raw_value, dict):
            return EMPTY_VALUE

        for value in raw_value:
            if not isinstance(value, str):
                return EMPTY_VALUE

        raw_value = [value for value in raw_value if value]
        parsed_value = {}
        for label in raw_value:
            if ":" not in label:
                return EMPTY_VALUE
            key, value = label.split(":", 1)
            parsed_value[key] = value

        return parsed_value

    def _validators(self) -> Sequence[Callable[[Mapping[str, str]], object]]:
        # Todo: Implement custom validation
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def _to_vue(
        self, raw_value: object, parsed_value: Mapping[str, str] | EmptyValue
    ) -> tuple[shared_type_defs.Labels, Mapping[str, str]]:
        if isinstance(parsed_value, EmptyValue):
            parsed_value = {}

        title, help_text = get_title_and_help(self.form_spec)

        return (
            shared_type_defs.Labels(
                title=title,
                help=help_text,
                i18n=shared_type_defs.LabelsI18n(
                    add_some_labels=translate_to_current_language("Add some labels"),
                    key_value_format_error=translate_to_current_language(
                        "Labels need to be in the format [KEY]:[VALUE]. For example os:windows."
                    ),
                    max_labels_reached=translate_to_current_language("Max labels reached"),
                    uniqueness_error=translate_to_current_language("Labels need to be unique."),
                ),
                validators=build_vue_validators(self._validators()),
                autocompleter=shared_type_defs.Autocompleter(
                    fetch_method="ajax_vs_autocomplete",
                    data={"ident": "label", "params": {"world": self.form_spec.world.value}},
                ),
                max_labels=self.form_spec.max_labels,
            ),
            {} if isinstance(parsed_value, EmptyValue) else parsed_value,
        )

    def _validate(
        self, raw_value: object, parsed_value: Mapping[str, str] | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return []

        for key, value in parsed_value.items():
            if ":" not in key or key == "" or value == "":
                return create_validation_error(
                    raw_value,
                    Title("Labels need to be in the format [KEY]:[VALUE]. For example os:windows."),
                )

        unique_pairs = set()
        for key, value in parsed_value.items():
            pair = (key, value)
            if pair in unique_pairs:
                return create_validation_error(
                    raw_value,
                    Title("Labels need to be unique."),
                )
            unique_pairs.add(pair)

        return compute_validation_errors(self._validators(), parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: Mapping[str, str]) -> Mapping[str, str]:
        return parsed_value

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable, Sequence

from cmk.gui.form_specs.private.folder import Folder
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1 import Message, Title
from cmk.rulesets.v1.form_specs import validators

from ._base import FormSpecVisitor
from ._type_defs import DEFAULT_VALUE, DefaultValue, EMPTY_VALUE, EmptyValue
from ._utils import compute_validation_errors, create_validation_error, get_title_and_help, localize


class FolderVisitor(FormSpecVisitor[Folder, str]):
    def _parse_value(self, raw_value: object) -> str | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                input_hint_default := self.form_spec.input_hint,
                EmptyValue,
            ):
                return input_hint_default
            raw_value = input_hint_default

        if not isinstance(raw_value, str):
            return EMPTY_VALUE
        return raw_value

    def _validators(self) -> Sequence[Callable[[str], object]]:
        FOLDER_PATTERN = (
            r"^(?:[~\\\/]?[-_ a-zA-Z0-9.]{1,32}(?:[~\\\/][-_ a-zA-Z0-9.]{1,32})*[~\\\/]?|[~\\\/]?)$"
        )
        default_validators = [
            validators.MatchRegex(
                regex=FOLDER_PATTERN,
                error_msg=Message("Invalid characters in %s") % localize(self.form_spec.title),
            )
        ]
        return default_validators + (
            list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []
        )

    def _to_vue(
        self, raw_value: object, parsed_value: str | EmptyValue
    ) -> tuple[shared_type_defs.Folder, str]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            shared_type_defs.Folder(
                title=title,
                help=help_text,
                validators=build_vue_validators(self._validators()),
                input_hint=self.form_spec.input_hint,
            ),
            "" if isinstance(parsed_value, EmptyValue) else parsed_value,
        )

    def _validate(
        self, raw_value: object, parsed_value: str | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(
                "" if raw_value == DEFAULT_VALUE else raw_value, Title("Invalid folder")
            )

        return compute_validation_errors(self._validators(), parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: str) -> str:
        return parsed_value

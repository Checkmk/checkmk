#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence

from cmk.ccc.i18n import _

from cmk.gui.form_specs.private.folder import Folder
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs import validators
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, InvalidValue
from ._utils import (
    get_title_and_help,
    localize,
)

_ParsedValueModel = str
_FrontendModel = str


class FolderVisitor(FormSpecVisitor[Folder, _ParsedValueModel, _FrontendModel]):
    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        if isinstance(raw_value, DefaultValue):
            if self.form_spec.input_hint is not None:
                return self.form_spec.input_hint
            return InvalidValue(reason=_("Using default value"), fallback_value="")

        if not isinstance(raw_value, str):
            return InvalidValue(reason=_("Invalid choice"), fallback_value="")
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
        self, raw_value: object, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.Folder, _FrontendModel]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            shared_type_defs.Folder(
                title=title,
                help=help_text,
                validators=build_vue_validators(self._validators()),
                input_hint=self.form_spec.input_hint,
            ),
            "" if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    def _to_disk(self, parsed_value: str) -> str:
        return parsed_value

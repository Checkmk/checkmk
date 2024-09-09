#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
from typing import Callable, Sequence

from cmk.gui.form_specs.converter import SimplePassword
from cmk.gui.form_specs.private import not_empty
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.utils.encrypter import Encrypter

from cmk.rulesets.v1 import Title

from ._base import FormSpecVisitor
from ._type_defs import DataOrigin, DefaultValue, EMPTY_VALUE, EmptyValue
from ._utils import (
    compute_validators,
    create_validation_error,
    get_title_and_help,
    optional_validation,
)

DecryptedPassword = str
EncryptedPassword = str
VuePassword = tuple[str, bool]


class SimplePasswordVisitor(FormSpecVisitor[SimplePassword, str]):
    def _parse_value(self, raw_value: object) -> DecryptedPassword | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            return EMPTY_VALUE

        if self.options.data_origin == DataOrigin.DISK:
            if not isinstance(raw_value, str):
                return EMPTY_VALUE
            return raw_value

        if not isinstance(raw_value, list):
            return EMPTY_VALUE
        password, encrypted = raw_value
        if not isinstance(password, str):
            return EMPTY_VALUE

        return (
            Encrypter.decrypt(base64.b64decode(password.encode("ascii"))) if encrypted else password
        )

    def _validators(self) -> Sequence[Callable[[str], object]]:
        return [not_empty()] + compute_validators(self.form_spec)

    def _to_vue(
        self, raw_value: object, parsed_value: DecryptedPassword | EmptyValue
    ) -> tuple[shared_type_defs.SimplePassword, VuePassword]:
        title, help_text = get_title_and_help(self.form_spec)
        if isinstance(parsed_value, EmptyValue):
            encrypted_password = ""
        else:
            encrypted_password = base64.b64encode(Encrypter.encrypt(parsed_value)).decode("ascii")

        return (
            shared_type_defs.SimplePassword(
                title=title,
                help=help_text,
                validators=build_vue_validators(self._validators()),
            ),
            (encrypted_password, bool(encrypted_password)),
        )

    def _validate(
        self, raw_value: object, parsed_value: DecryptedPassword | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error("", Title("No password provided"))
        return [
            shared_type_defs.ValidationMessage(location=[], message=x, invalid_value="")
            for x in optional_validation(self._validators(), parsed_value)
            if x is not None
        ]

    def _to_disk(self, raw_value: object, parsed_value: DecryptedPassword) -> object:
        return parsed_value

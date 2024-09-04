#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
from typing import Literal

from cmk.utils.password_store import ad_hoc_password_id

from cmk.gui.form_specs.vue import shared_type_defs as VueComponents
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _
from cmk.gui.utils.encrypter import Encrypter
from cmk.gui.watolib.password_store import passwordstore_choices

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Password

from ._base import FormSpecVisitor
from ._type_defs import DataOrigin, DefaultValue, EMPTY_VALUE, EmptyValue
from ._utils import (
    compute_validators,
    create_validation_error,
    get_title_and_help,
    optional_validation,
)

PasswordId = str
ParsedPassword = tuple[
    Literal["cmk_postprocessed"],
    Literal["explicit_password", "stored_password"],
    tuple[PasswordId, str],
]
Encrypted = bool
VuePassword = tuple[Literal["explicit_password", "stored_password"], PasswordId, str, Encrypted]


class PasswordVisitor(FormSpecVisitor[Password, ParsedPassword]):
    def _parse_value(self, raw_value: object) -> ParsedPassword | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            return EMPTY_VALUE

        if not isinstance(raw_value, (tuple, list)):
            return EMPTY_VALUE

        match self.options.data_origin:
            case DataOrigin.DISK:
                if not raw_value[0] == "cmk_postprocessed":
                    return EMPTY_VALUE
                try:
                    password_type, (password_id, password) = raw_value[1:]
                except (TypeError, ValueError):
                    return EMPTY_VALUE
                encrypted = False
            case DataOrigin.FRONTEND:
                try:
                    password_type, password_id, password, encrypted = raw_value
                except (TypeError, ValueError):
                    return EMPTY_VALUE
            case _:
                # Unreachable, just here for type checking
                raise NotImplementedError

        if password_type not in (
            "explicit_password",
            "stored_password",
        ):
            return EMPTY_VALUE

        if (
            not isinstance(password_id, str)
            or not isinstance(password, str)
            or not isinstance(encrypted, bool)
        ):
            return EMPTY_VALUE

        if encrypted:
            password = Encrypter.decrypt(base64.b64decode(password.encode("ascii")))

        return "cmk_postprocessed", password_type, (password_id, password)

    def _to_vue(
        self, raw_value: object, parsed_value: ParsedPassword | EmptyValue
    ) -> tuple[VueComponents.Password, VuePassword]:
        title, help_text = get_title_and_help(self.form_spec)
        value = (
            ("explicit_password", "", "", False)
            if isinstance(parsed_value, EmptyValue)
            else (
                parsed_value[1],
                parsed_value[2][0],
                base64.b64encode(Encrypter.encrypt(parsed_value[2][1])).decode("ascii"),
                True,
            )
        )
        return (
            VueComponents.Password(
                title=title,
                help=help_text,
                validators=build_vue_validators(compute_validators(self.form_spec)),
                password_store_choices=[
                    VueComponents.PasswordStoreChoice(password_id=pw_id, name=pw_name)
                    for pw_id, pw_name in passwordstore_choices()
                    if pw_id is not None
                ],
                i18n=VueComponents.I18nPassword(
                    explicit_password=_("Explicit"),
                    password_store=_("From password store"),
                    no_password_store_choices=_(
                        "There are no elements defined for this selection yet."
                    ),
                    password_choice_invalid=_("Password does not exist or using not permitted."),
                ),
            ),
            value,
        )

    def _validate(
        self, raw_value: object, parsed_value: ParsedPassword | EmptyValue
    ) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error("", Title("No password provided"))
        if parsed_value[1] == "explicit_password":
            return [
                VueComponents.ValidationMessage(location=[], message=x, invalid_value="")
                for x in optional_validation(compute_validators(self.form_spec), parsed_value[2][1])
                if x is not None
            ]
        return []

    def _to_disk(self, raw_value: object, parsed_value: ParsedPassword) -> object:
        if self.options.data_origin == DataOrigin.DISK:
            return raw_value
        postprocessed, password_type, (password_id, password) = parsed_value
        if password_type == "explicit_password" and not password_id:
            password_id = ad_hoc_password_id()
        return (postprocessed, password_type, (password_id, password))

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
from typing import Literal

from cmk.utils.password_store import ad_hoc_password_id

from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _
from cmk.gui.utils.encrypter import Encrypter
from cmk.gui.watolib.password_store import passwordstore_choices

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Password
from cmk.shared_typing import vue_formspec_components as VueComponents

from ._base import FormSpecVisitor
from ._type_defs import DataOrigin, DefaultValue, InvalidValue
from ._utils import (
    base_i18n_form_spec,
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


class PasswordVisitor(FormSpecVisitor[Password, ParsedPassword, VuePassword]):
    def _parse_value(self, raw_value: object) -> ParsedPassword | InvalidValue[VuePassword]:
        fallback_value: VuePassword = ("explicit_password", "", "", False)
        if isinstance(raw_value, DefaultValue):
            return InvalidValue(reason=_("No password provided"), fallback_value=fallback_value)

        if not isinstance(raw_value, tuple | list):
            return InvalidValue(reason=_("No password provided"), fallback_value=fallback_value)

        match self.options.data_origin:
            case DataOrigin.DISK:
                if not raw_value[0] == "cmk_postprocessed":
                    return InvalidValue(
                        reason=_("No password provided"), fallback_value=fallback_value
                    )
                try:
                    password_type, (password_id, password) = raw_value[1:]
                except (TypeError, ValueError):
                    return InvalidValue(
                        reason=_("No password provided"), fallback_value=fallback_value
                    )
                encrypted = False
            case DataOrigin.FRONTEND:
                try:
                    password_type, password_id, password, encrypted = raw_value
                except (TypeError, ValueError):
                    return InvalidValue(
                        reason=_("No password provided"), fallback_value=fallback_value
                    )
            case _:
                # Unreachable, just here for type checking
                raise NotImplementedError

        if password_type not in (
            "explicit_password",
            "stored_password",
        ):
            return InvalidValue(reason=_("Invalid data format"), fallback_value=fallback_value)

        if (
            not isinstance(password_id, str)
            or not isinstance(password, str)
            or not isinstance(encrypted, bool)
        ):
            return InvalidValue(reason=_("Invalid data format"), fallback_value=fallback_value)

        if encrypted:
            password = Encrypter.decrypt(base64.b64decode(password.encode("ascii")))

        return "cmk_postprocessed", password_type, (password_id, password)

    def _to_vue(
        self, parsed_value: ParsedPassword | InvalidValue[VuePassword]
    ) -> tuple[VueComponents.Password, VuePassword]:
        title, help_text = get_title_and_help(self.form_spec)
        value: VuePassword = (
            parsed_value.fallback_value
            if isinstance(parsed_value, InvalidValue)
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
                    choose_password_type=_("Choose password type"),
                    choose_password_from_store=_("Choose password from store"),
                    explicit_password=_("Explicit"),
                    password_store=_("From password store"),
                    no_password_store_choices=_(
                        "There are no elements defined for this selection yet."
                    ),
                    password_choice_invalid=_("Password does not exist or using not permitted."),
                ),
                i18n_base=base_i18n_form_spec(),
            ),
            value,
        )

    def _validate(self, parsed_value: ParsedPassword) -> list[VueComponents.ValidationMessage]:
        if parsed_value[1] == "explicit_password":
            return [
                VueComponents.ValidationMessage(location=[], message=x, replacement_value="")
                for x in optional_validation(compute_validators(self.form_spec), parsed_value[2][1])
                if x is not None
            ]
        if parsed_value[1] == "stored_password":
            if not parsed_value[2][0]:
                return create_validation_error("", Title("No password selected"))

        return []

    def _to_disk(self, parsed_value: ParsedPassword) -> ParsedPassword:
        postprocessed, password_type, (password_id, password) = parsed_value
        if password_type == "explicit_password" and not password_id:
            password_id = ad_hoc_password_id()
        return (postprocessed, password_type, (password_id, password))

    def _mask(self, parsed_value: ParsedPassword) -> ParsedPassword:
        postprocessed, password_type, (password_id, _) = self._to_disk(parsed_value)
        return (postprocessed, password_type, (password_id, "******"))

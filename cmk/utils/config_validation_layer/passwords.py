#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from pydantic import BaseModel, RootModel, ValidationError

from cmk.utils.config_validation_layer.type_defs import Omitted, OMITTED_FIELD
from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError


class PasswordModel(BaseModel):
    title: str
    comment: str
    docu_url: str
    password: str
    owned_by: str | None
    shared_with: list[str]
    customer: str | None | Omitted = OMITTED_FIELD


PasswordMapModel = RootModel[dict[str, PasswordModel]]


def validate_passwords(passwords: dict | Mapping) -> None:
    if isinstance(passwords, Mapping):
        passwords = dict(passwords)

    try:
        PasswordMapModel(passwords)
    except ValidationError as exc:
        raise ConfigValidationError(
            which_file="passwords.mk",
            pydantic_error=exc,
            original_data=passwords,
        )

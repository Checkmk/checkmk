#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import typing

from cmk.rulesets.v1._localize import Message
from cmk.rulesets.v1.form_specs import validators

T = typing.TypeVar("T")

ModelT = typing.TypeVar("ModelT")

ValidatorType = typing.Callable[[ModelT], None]


class EnforceSuffix:
    def __init__(
        self,
        suffix: str,
        *,
        case: typing.Literal["ignore", "sensitive"],
        error_msg: Message = Message("Does not end with %s"),
    ) -> None:
        self.suffix = suffix
        self.case = case
        self.error_msg = error_msg

    def __call__(self, value: str) -> None:
        if self.case == "ignore":
            to_check = value.lower()
            suffix = self.suffix.lower()
        else:
            to_check = value
            suffix = self.suffix

        if not to_check.endswith(suffix):
            raise validators.ValidationError(self.error_msg % suffix)

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from cmk.gui.exceptions import MKUserError
from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.shared_typing.vue_formspec_components import ValidationMessage

DiskModel = Any


class DefaultValue:
    pass


DEFAULT_VALUE = DefaultValue()


@dataclass(frozen=True)
class RawFrontendData:
    value: object


@dataclass(frozen=True)
class RawDiskData:
    value: object


IncomingData = RawFrontendData | RawDiskData | DefaultValue
_ModelT = TypeVar("_ModelT")


@dataclass
class InvalidValue(Generic[_ModelT]):
    fallback_value: _ModelT
    reason: str


class FormSpecValidationError(ValueError):
    def __init__(self, messages: list[ValidationMessage]) -> None:
        super().__init__(messages)
        self._messages = messages

    @property
    def messages(self) -> list[ValidationMessage]:
        return self._messages


T = TypeVar("T", bound=object)


def create_validation_error_for_mk_user_error(
    wrapped_function: Callable[[T], None],
) -> Callable[[T], None]:
    def wrapped(value: T) -> None:
        try:
            wrapped_function(value)
        except MKUserError as e:
            raise ValidationError(message=Message(str(e)))  # pylint: disable=localization-of-non-literal-string

    return wrapped


@dataclass(kw_only=True)
class VisitorOptions:
    migrate_values: bool
    mask_values: bool

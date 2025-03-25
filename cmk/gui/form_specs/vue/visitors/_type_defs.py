#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from enum import auto, Enum
from typing import Any, Generic, TypeVar

from cmk.shared_typing.vue_formspec_components import ValidationMessage

DiskModel = Any
FrontendModel = TypeVar("FrontendModel")
ParsedValueModel = TypeVar("ParsedValueModel")


class DefaultValue:
    pass


DEFAULT_VALUE = DefaultValue()


class Unset:
    pass


UNSET = Unset()


class DataOrigin(Enum):
    DISK = auto()
    FRONTEND = auto()


@dataclass
class VisitorOptions:
    # Depending on the origin, we will call the migrate function
    data_origin: DataOrigin


@dataclass
class InvalidValue(Generic[FrontendModel]):
    fallback_value: FrontendModel
    reason: str


class FormSpecValidationError(ValueError):
    def __init__(self, messages: list[ValidationMessage]) -> None:
        super().__init__(messages)
        self._messages = messages

    @property
    def messages(self) -> list[ValidationMessage]:
        return self._messages

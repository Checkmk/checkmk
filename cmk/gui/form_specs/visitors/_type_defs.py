#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.shared_typing.vue_formspec_components import ValidationMessage


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


@dataclass
class InvalidValue[ModelT]:
    fallback_value: ModelT
    reason: str


class FormSpecValidationError(ValueError):
    def __init__(self, messages: list[ValidationMessage]) -> None:
        super().__init__(messages)
        self._messages = messages

    @property
    def messages(self) -> list[ValidationMessage]:
        return self._messages


@dataclass(kw_only=True)
class VisitorOptions:
    migrate_values: bool
    mask_values: bool

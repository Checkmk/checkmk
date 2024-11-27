#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from enum import auto, Enum
from typing import Any

from cmk.gui.form_specs.vue.shared_type_defs import ValidationMessage

DataForDisk = Any


class DefaultValue:
    pass


DEFAULT_VALUE = DefaultValue()


class DataOrigin(Enum):
    DISK = auto()
    FRONTEND = auto()


@dataclass
class VisitorOptions:
    # Depending on the origin, we will call the migrate function
    data_origin: DataOrigin


class EmptyValue:
    pass


EMPTY_VALUE = EmptyValue()


class FormSpecValidationError(ValueError):
    def __init__(self, messages: list[ValidationMessage]) -> None:
        super().__init__(messages)
        self._messages = messages

    @property
    def messages(self) -> list[ValidationMessage]:
        return self._messages

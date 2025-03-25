#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import uuid
from typing import Self

from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Request


class SelectionId(str):
    def __new__(cls, text: str) -> Self:
        cls.validate(text)
        return super().__new__(cls, text)

    @staticmethod
    def validate(text: str) -> None:
        if not re.match("^[-0-9a-zA-Z]+$", text):
            raise ValueError(f"Forbidden chars for SelectionId in {text!r}")

    @classmethod
    def generate(cls) -> Self:
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_request(cls, request: Request) -> Self:
        try:
            return request.get_validated_type_input_mandatory(cls, "selection")
        except MKUserError:
            request.set_var("selection", new_id := cls.generate())
            return new_id

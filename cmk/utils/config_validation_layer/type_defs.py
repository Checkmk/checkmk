#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from pydantic import Field


class Omitted:
    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> "Omitted":
        return cls()


def omitted_value() -> Any:
    return Omitted()


OMITTED_FIELD = Field(default_factory=omitted_value)

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, validator

from .markup import markdown_to_html, nowiki_to_markdown


class Edition(Enum):
    # would love to use cmk.utils.version.Edition
    # but pydantic does not understand it.
    CRE = "cre"
    CSE = "cse"
    CEE = "cee"
    CCE = "cce"
    CME = "cme"
    CFE = "cfe"


class Level(Enum):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


class Compatibility(Enum):
    COMPATIBLE = "yes"
    NOT_COMPATIBLE = "no"


class Class(Enum):
    FEATURE = "feature"
    FIX = "fix"
    SECURITY = "security"


class WerkV2Base(BaseModel):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.

    class Config:
        extra = "forbid"
        populate_by_name = True

    werk_version: Literal["2"] = Field(default="2", alias="__version__")
    id: int
    class_: Class = Field(alias="class")
    component: str
    level: Level
    date: datetime.datetime
    compatible: Compatibility
    edition: Edition
    description: str
    title: str

    @validator("level", pre=True)
    @classmethod
    def parse_level(cls, v: str) -> Level:
        if isinstance(v, Level):
            return v
        try:
            return Level(int(v))
        except ValueError as e:
            raise ValueError(f"Expected level to be in (1, 2, 3). Got {v} instead") from e

    def to_json_dict(self) -> dict[str, object]:
        return self.dict(by_alias=True)  # TODO: mode json


class Werk(WerkV2Base):
    class Config:
        extra = "forbid"
        populate_by_name = True

    version: str

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Werk:
        return cls.parse_obj(data)


class WerkV1(BaseModel):
    class Config:
        extra = "forbid"

    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.

    # ATTENTION! you can not change this model, its only for parsing
    # existing precompiled werks from checkmk 2.2.

    class_: str = Field(alias="class")
    component: str
    date: int
    level: int
    title: str
    version: str
    compatible: str
    edition: str
    knowledge: str | None = (
        None  # this field is currently not used, but kept so parsing still works
    )
    # it will be removed after the transfer to markdown werks was completed.
    state: str | None = None
    id: int
    targetversion: str | None = None
    description: list[str]

    def to_werk(self) -> Werk:
        return Werk(
            compatible=(
                Compatibility.COMPATIBLE
                if self.compatible == "compat"
                else Compatibility.NOT_COMPATIBLE
            ),
            version=self.version,
            title=self.title,
            id=self.id,
            date=datetime.datetime.fromtimestamp(self.date, tz=datetime.UTC),
            description=markdown_to_html(nowiki_to_markdown(self.description)),
            level=Level(self.level),
            class_=Class(self.class_),  # type: ignore[call-arg]
            component=self.component,
            edition=Edition(self.edition),
        )

    def to_json_dict(self) -> dict[str, object]:
        return self.dict(by_alias=True)

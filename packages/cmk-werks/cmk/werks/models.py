#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, TypeAdapter

from .markup import markdown_to_html, nowiki_to_markdown


class EditionV2(Enum):
    # would love to use cmk.ccc.version.Edition
    # but pydantic does not understand it.
    CRE = "cre"
    CEE = "cee"
    CCE = "cce"
    CME = "cme"
    CSE = "cse"


class EditionV3(Enum):
    COMMUNITY = "community"
    PRO = "pro"
    ULTIMATE = "ultimate"
    ULTIMATEMT = "ultimatemt"
    CLOUD = "cloud"


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


class WerkV3Base(BaseModel):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    werk_version: Literal["3"] = Field(default="3", alias="__version__")
    id: int
    class_: Class = Field(alias="class")
    component: str
    level: Level
    date: datetime.datetime
    compatible: Compatibility
    edition: EditionV3
    description: str
    title: str

    @field_validator("level", mode="before")
    @classmethod
    def parse_level(cls, v: str) -> Level:
        if isinstance(v, Level):
            return v
        try:
            return Level(int(v))
        except ValueError as e:
            raise ValueError(f"Expected level to be in (1, 2, 3). Got {v} instead") from e

    def to_json_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, mode="json")


class WerkV2Base(BaseModel):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    werk_version: Literal["2"] = Field(default="2", alias="__version__")
    id: int
    class_: Class = Field(alias="class")
    component: str
    level: Level
    date: datetime.datetime
    compatible: Compatibility
    edition: EditionV2
    description: str
    title: str

    @field_validator("level", mode="before")
    @classmethod
    def parse_level(cls, v: str) -> Level:
        if isinstance(v, Level):
            return v
        try:
            return Level(int(v))
        except ValueError as e:
            raise ValueError(f"Expected level to be in (1, 2, 3). Got {v} instead") from e

    def to_json_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, mode="json")


class WerkV3(WerkV3Base):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    version: str

    @classmethod
    def from_json(cls, data: dict[str, object]) -> WerkV3:
        return cls.model_validate(data)


class WerkV2(WerkV2Base):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    version: str

    @classmethod
    def from_json(cls, data: dict[str, object]) -> WerkV2:
        return cls.model_validate(data)


class WerkV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

    def to_werk(self) -> WerkV2:
        return WerkV2(
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
            class_=Class(self.class_),
            component=self.component,
            edition=EditionV2(self.edition),
        )

    def to_json_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True)


class WebsiteWerkV2(WerkV2Base):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.
    """
    This Model is used to built up a file containing all werks.
    The file is called all_werks.json or all_werks_v2.json
    """

    versions: dict[str, str]
    product: Literal["cmk", "cma", "checkmk_kube_agent", "cloudmk"]


class WebsiteWerkV3(WerkV3Base):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.
    """
    This Model is used to built up a file containing all werks.
    The file is called all_werks.json or all_werks_v2.json
    """

    versions: dict[str, str]
    product: Literal["cmk", "cma", "checkmk_kube_agent", "cloudmk"]


# ATTENTION! If you change this model, you have to inform
# the website team first! They rely on those fields.
# The key of the dict is the werk id
AllWerks = TypeAdapter(dict[str, WebsiteWerkV2 | WebsiteWerkV3])

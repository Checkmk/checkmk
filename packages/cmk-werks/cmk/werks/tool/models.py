#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter


class Level(Enum):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


def _parse_level(v: object) -> Level:
    if isinstance(v, Level):
        return v
    try:
        if not isinstance(v, int | float | str):
            raise ValueError(v)
        return Level(int(v))
    except ValueError as e:
        raise ValueError(f"Expected level to be in (1, 2, 3). Got {v} instead") from e


ParsedLevel = Annotated[Level, BeforeValidator(_parse_level)]


class Compatibility(Enum):
    COMPATIBLE = "yes"
    NOT_COMPATIBLE = "no"


class WebsiteWerkV3Base(BaseModel):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    werk_version: Literal["3"] = Field(default="3", alias="__version__")
    id: int
    class_: str = Field(alias="class")
    component: str
    level: ParsedLevel
    date: datetime.datetime
    compatible: Compatibility
    edition: str
    description: str
    title: str


class WebsiteWerkV2Base(BaseModel):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    werk_version: Literal["2"] = Field(default="2", alias="__version__")
    id: int
    class_: str = Field(alias="class")
    component: str
    level: ParsedLevel
    date: datetime.datetime
    compatible: Compatibility
    edition: str
    description: str
    title: str


class WebsiteWerkV2(WebsiteWerkV2Base):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.
    """
    This Model is used to built up a file containing all werks.
    The file is called all_werks.json or all_werks_v2.json
    """

    versions: dict[str, str]
    product: Literal["cmk", "cma", "checkmk_kube_agent", "cloudmk"]


class WebsiteWerkV3(WebsiteWerkV3Base):
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

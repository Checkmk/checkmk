#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime

from pydantic import BaseModel, ConfigDict, Field

from .convert import nowiki_to_markdown
from .werk import Class, Compatibility, Edition, Level, Werk
from .werkv2 import markdown_to_html


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
            class_=Class(self.class_),
            component=self.component,
            edition=Edition(self.edition),
        )

    def to_json_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True)

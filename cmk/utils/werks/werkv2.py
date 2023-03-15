#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from pathlib import Path
from typing import Any, Literal

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from pydantic import BaseModel, Field, validator
from pydantic.error_wrappers import ValidationError

from cmk.utils.version import parse_check_mk_version

from .werk import Class, Compatibility, Edition, Level, RawWerk, Werk, WerkError, WerkTranslator


class RawWerkV2(BaseModel, RawWerk):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.
    werk_version: Literal["2"] = Field(default="2", alias="__version__")
    id: int
    class_: Class = Field(alias="class")
    component: str
    level: Level
    date: datetime.datetime
    version: str
    compatible: Compatibility
    edition: Edition = Field(json_encoders=lambda x: x.short)
    description: str
    title: str

    @validator("version")
    def parse_version(cls, v: str) -> str:  # pylint: disable=no-self-argument
        parse_check_mk_version(v)
        return v

    @validator("level", pre=True)
    def parse_level(cls, v: str) -> Level:  # pylint: disable=no-self-argument
        try:
            return Level(int(v))
        except ValueError:
            raise ValueError(f"Expected level to be in (1, 2, 3). Got {v} instead")

    @validator("component")
    def parse_component(cls, v: str) -> str:  # pylint: disable=no-self-argument
        components = set(k for k, _ in WerkTranslator().components())
        if v not in components:
            raise TypeError(f"Component {v} not know. Choose from: {components}")
        return v

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "RawWerkV2":

        return cls.parse_obj(data)

    def to_json_dict(self) -> dict[str, object]:
        return {
            "__version__": self.werk_version,
            "id": self.id,
            "class": self.class_.value,
            "compatible": self.compatible.value,
            "component": self.component,
            "date": self.date.isoformat(),
            "edition": self.edition.value,
            "level": self.level.value,
            "title": self.title,
            "version": self.version,
            "description": str(self.description),
        }

    def to_werk(self) -> "Werk":
        return Werk(
            compatible=self.compatible,
            version=self.version,
            title=self.title,
            id=self.id,
            date=self.date,
            description=self.description,
            level=self.level,
            class_=self.class_,
            component=self.component,
            edition=self.edition,
        )


def load_werk_v2(path: Path, werk_id: str) -> RawWerkV2:
    with path.open(encoding="utf-8") as fp:
        werk_raw = fp.read()

    # no need to parse the werk version here. markdown version and werk version
    # could potentially be different: a markdown version 3 could be parsed to a
    # werk version 2. let's hope we will keep v2 for a long time :-)
    if not werk_raw.startswith("[//]: # (werk v2)"):
        raise WerkError("Markdown formatted werks need to start with '[//]: # (werk v2)'")

    class WerkExtractor(Treeprocessor):
        def __init__(self, werk):
            super().__init__()
            self._werk = werk

        def run(self, root):
            headline = root[0]
            if headline.tag != "h1":
                raise WerkError(
                    "First element after the header needs to be the title as a h1 headline. The line has to start with '#'."
                )
            self._werk["title"] = headline.text
            root.remove(headline)

            # we removed the headline so we can access element 0 again with a
            # different result.
            table = root[0]
            if table.tag != "table":
                raise WerkError(f"Expected a table after the title, found '{table.tag}'")
            tbody = table.findall("./tbody/")
            for table_tr in tbody:
                key, value = table_tr.findall("./td")
                self._werk[key.text] = value.text
            root.remove(root.findall("./table")[0])

    class WerkExtractorExtension(Extension):
        def __init__(self, werk):
            super().__init__()
            self._werk = werk

        def extendMarkdown(self, md):
            md.treeprocessors.register(WerkExtractor(self._werk), "werk", 100)

    werk: dict[str, object] = {
        "__version__": "2",
        "id": werk_id,
    }
    result = markdown.markdown(
        werk_raw, extensions=["tables", WerkExtractorExtension(werk)], output_format="html"
    )

    # werk was passed by reference into WerkExtractorExtension which got passed
    # to WerkExtractor which wrote all the fields.
    werk["description"] = result

    try:
        return RawWerkV2.parse_obj(werk)
    except ValidationError as e:
        raise WerkError(f"Error validating werk:\n{werk}\nerror:\n{e}") from e

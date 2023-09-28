#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for processing Checkmk werks. This is needed by several components,
so it's best place is in the central library.

We are currently in the progress of moving the werk files from nowiki syntax to
markdown. The files written by the developers (in `.werks` folder in this repo)
contain markdown if the filenames ends with `.md`, otherwise nowiki syntax.

In order to speed up the loading of the werk files they are precompiled and
packaged as json during release. Pydantic model Werk is used to handle the
serializing and deserializing.

But all this should be implementation details, because downstream tools should
only handle the WerkV2 model. Old style werks are converted to markdown Werks,
so both can be handled with a common interface.
"""
import itertools
from pathlib import Path
from typing import IO, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field, RootModel, TypeAdapter

import cmk.utils.paths

from .convert import werkv1_to_werkv2
from .werk import Class, Compatibility, sort_by_version_and_component, Werk, WerkTranslator
from .werkv1 import parse_werk_v1
from .werkv2 import load_werk_v2, parse_werk_v2, WerkV2ParseResult

Werks = RootModel[dict[int, Werk]]


class GuiWerkProtocol(Protocol):
    werk: Werk
    acknowledged: bool


GWP = TypeVar("GWP", bound=GuiWerkProtocol)


def _compiled_werks_dir() -> Path:
    return Path(cmk.utils.paths.share_dir, "werks")


def load(base_dir: Path | None = None) -> dict[int, Werk]:
    if base_dir is None:
        base_dir = _compiled_werks_dir()

    werks: dict[int, Werk] = {}
    for file_name in [(base_dir / "werks"), *base_dir.glob("werks-*")]:
        werks.update(load_precompiled_werks_file(file_name))
    return werks


def load_precompiled_werks_file(path: Path) -> dict[int, Werk]:
    # ? what is the content of these files, to which the path shows
    adapter = TypeAdapter(dict[int, Werk])
    with path.open("r", encoding="utf-8") as f:
        return adapter.validate_json(f.read())


# THIS IS A TEMPORARY FIX FOR THE OLD WORKFLOW


class OldWerk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.
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

    def to_json_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True)


def load_raw_files_old(werks_dir: Path) -> list[OldWerk]:
    if werks_dir is None:
        werks_dir = _compiled_werks_dir()
    werks: list[OldWerk] = []
    for file_name in werks_dir.glob("[0-9]*"):
        try:
            parsed = parse_werk_v1(file_name.read_text(), int(file_name.name))
            werk: dict[str, str | int | list[str]] = {}
            werk.update(parsed.metadata)
            werk["description"] = parsed.description
            werks.append(OldWerk.model_validate(werk))
        except Exception as e:
            raise RuntimeError(f"Could not parse werk {file_name.absolute()}") from e
    return werks


# TEMPORARY FIX END!


def load_raw_files(werks_dir: Path) -> list[Werk]:
    if werks_dir is None:
        werks_dir = _compiled_werks_dir()
    werks: list[Werk] = []
    for file_name in werks_dir.glob("[0-9]*"):
        try:
            werks.append(load_werk(file_content=file_name.read_text(), file_name=file_name.name))
        except Exception as e:
            raise RuntimeError(f"Could not parse werk {file_name.absolute()}") from e
    return werks


def write_precompiled_werks(path: Path, werks: dict[int, Werk]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        fp.write(Werks.model_validate(werks).model_dump_json(by_alias=True))


# this function is used from the bauwelt repo. TODO: move script from bauwelt into this repo
# TODO: use a jinja template for this, and move it to .announce
def write_as_text(werks: dict[int, Werk], f: IO[str], write_version: bool = True) -> None:
    """Write the given werks to a file object

    This is used for creating a textual hange log for the released versions.
    """
    # TODO: reuse code from  .announce and replace with two jinja templates, one for txt, one for markdown
    translator = WerkTranslator()
    werklist = sort_by_version_and_component(werks.values())
    for version, version_group in itertools.groupby(werklist, key=lambda w: w.version):
        # write_version=False is used by the announcement mails
        if write_version:
            f.write("%s:\n" % version)
        for component, component_group in itertools.groupby(
            version_group, key=translator.component_of
        ):
            f.write("    %s:\n" % component)
            for werk in component_group:
                write_werk_as_text(f, werk)
            f.write("\n")
        f.write("\n")


def has_content(description: str) -> bool:
    return bool(description.strip())


def write_werk_as_text(f: IO[str], werk: Werk) -> None:
    # TODO: use jinja templates of .announce
    prefix = ""
    if werk.class_ == Class.FIX:
        prefix = " FIX:"
    elif werk.class_ == Class.SECURITY:
        prefix = " SEC:"

    # See following commits...
    if has_content(werk.description):
        omit = "..."
    else:
        omit = ""

    f.write(
        "    * %04d%s %s%s\n"
        % (
            werk.id,
            prefix,
            werk.title,
            omit,
        )
    )

    if werk.compatible == Compatibility.NOT_COMPATIBLE:
        f.write("            NOTE: Please refer to the migration notes!\n")


def load_werk(*, file_content: str, file_name: str) -> Werk:
    parsed = parse_werk(file_content, file_name)
    return load_werk_v2(parsed)


def parse_werk(file_content: str, file_name: str) -> WerkV2ParseResult:
    if file_name.endswith(".md"):
        return parse_werk_v2(file_content, file_name.removesuffix(".md"))
    file_content, werk_id = werkv1_to_werkv2(file_content, int(file_name))
    return parse_werk_v2(file_content, str(werk_id))  # TODO: str does not make sense!

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
packaged as json during release. Pydantic models RawWerkV1 (for nowiki) and
RawWerkV2 (for markdown) are used to handle the serializing and deserializing.

But all this should be implementation details, because downstream tools should
only handle the Werk NamedTuple, which unifies both formats.
"""

import itertools
from collections.abc import Iterable
from pathlib import Path
from typing import IO, Protocol, TypeVar

from pydantic import BaseModel, parse_file_as

import cmk.utils.paths
from cmk.utils.i18n import _

from .werk import Class, Compatibility, NoWiki, Werk, WerkError, WerkTranslator
from .werkv1 import load_werk_v1, RawWerkV1
from .werkv2 import load_werk_v2, RawWerkV2


class Werks(BaseModel):
    __root__: dict[int, RawWerkV1 | RawWerkV2]


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
    return {
        werk_id: werk.to_werk()
        for werk_id, werk in parse_file_as(dict[int, RawWerkV1 | RawWerkV2], path).items()
    }


def load_raw_files(werks_dir: Path) -> list[RawWerkV1 | RawWerkV2]:
    if werks_dir is None:
        werks_dir = _compiled_werks_dir()
    werks: list[RawWerkV1 | RawWerkV2] = []
    for file_name in werks_dir.glob("[0-9]*"):
        if file_name.name.endswith(".md"):
            werk2 = load_werk_v2(file_name.read_text(), werk_id=file_name.name.removesuffix(".md"))
            werks.append(werk2)
        else:
            werk_id = int(file_name.name)
            try:
                werks.append(load_werk_v1(file_name.read_text(), werk_id))
            except Exception as e:
                raise WerkError(_('Failed to load werk "%s": %s') % (werk_id, e)) from e
    return werks


def write_precompiled_werks(path: Path, werks: dict[int, RawWerkV1 | RawWerkV2]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        fp.write(Werks.parse_obj(werks).json(by_alias=True))


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


def has_content(description: NoWiki | str) -> bool:
    if isinstance(description, NoWiki):
        return bool(("".join(description.value)).strip())
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


class SortKeyProtocol(Protocol):
    def sort_by_version_and_component(self, translator: WerkTranslator) -> tuple[str | int, ...]:
        pass


T = TypeVar("T", bound=SortKeyProtocol)


# sort by version and within one version by component
def sort_by_version_and_component(werks: Iterable[T]) -> list[T]:
    translator = WerkTranslator()
    return sorted(werks, key=lambda w: w.sort_by_version_and_component(translator))

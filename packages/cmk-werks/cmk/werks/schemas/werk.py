#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import sys
from pathlib import Path
from typing import Literal, NamedTuple, override, TypeVar

from pydantic import BaseModel, Field

from ..in_out_elements import TTY_NORMAL, TTY_RED
from ..parse import WerkV2ParseResult, WerkV3ParseResult

T = TypeVar("T", bound="Stash")


class Stash(BaseModel):
    stash_version: Literal["2"] = Field(default="2", alias="__version__")
    ids_by_project: dict[str, list[int]] = Field(default={})

    def count(self) -> int:
        """
        total number of ids available in the stash
        """
        return sum(len(ids) for ids in self.ids_by_project.values())

    def pick_id(self, *, project: str) -> "WerkId":
        """
        the id will still be in the stash, but it could be freed next.
        """
        try:
            return WerkId(sorted(self.ids_by_project[project])[0])
        except (KeyError, IndexError) as e:
            raise RuntimeError(
                "You have no Werk IDs. You can reserve 10 additional Werk IDs with 'werk ids 10'."
            ) from e

    def free_id(self, werk_id: "WerkId") -> None:
        """
        remove id from stash
        """
        removed = False
        for project, ids in self.ids_by_project.items():
            if werk_id.id in ids:
                removed = True
                ids.remove(werk_id.id)
                if not ids:
                    sys.stdout.write(
                        f"\n{TTY_RED}"
                        f"This was your last reserved ID for project {project}"
                        f"{TTY_NORMAL}\n\n"
                    )

        if not removed:
            raise RuntimeError(f"Could not find werk_id {werk_id} in any project.")

    def add_id(self, werk_id: "WerkId", *, project: str) -> None:
        """
        put a id into the stash
        """
        # werks can be delete, but we don't want to lose the id, lets put it back to the stash
        if project not in self.ids_by_project:
            self.ids_by_project[project] = []
        self.ids_by_project[project].append(werk_id.id)


class WerkId:
    __slots__ = ("__id",)

    def __init__(self, id: int):  # noqa: A002
        self.__id = id

    @override
    def __repr__(self) -> str:
        return f"<WerkId {self.__id:0>5}>"

    @override
    def __str__(self) -> str:
        return f"{self.__id:0>5}"

    @property
    def id(self) -> int:
        return self.__id

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self.id == other.id
        return False

    @override
    def __hash__(self) -> int:
        return hash(self.__id)


class Werk(NamedTuple):
    path: Path
    id: WerkId
    content: WerkV2ParseResult | WerkV3ParseResult

    @property
    def date(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self.content.metadata["date"])

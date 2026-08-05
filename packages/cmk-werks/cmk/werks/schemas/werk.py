#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, NamedTuple, override

from pydantic import BaseModel, Field

from ..in_out_elements import TTY_NORMAL, TTY_RED
from ..parse import WerkV2ParseResult, WerkV3ParseResult


class Stash(BaseModel):
    stash_version: Literal["3"] = Field(default="3", alias="__version__")
    ids: list[int] = Field(default=[])

    def count(self) -> int:
        """
        total number of ids available in the stash
        """
        return len(self.ids)

    def pick_id(self) -> "WerkId":
        """
        the id will still be in the stash, but it could be freed next.
        """
        try:
            return WerkId(sorted(self.ids)[0])
        except (KeyError, IndexError) as e:
            raise RuntimeError(
                "You have no Werk IDs. Please ensure that you're in the VPN and the werk IDs "
                "server is reachable, then try again."
            ) from e

    def free_id(self, werk_id: "WerkId") -> None:
        """
        remove id from stash
        """
        removed = False
        if werk_id.id in self.ids:
            removed = True
            self.ids.remove(werk_id.id)
            if not self.ids:
                sys.stderr.write(
                    f"\n{TTY_RED}This was your last reserved ID{TTY_NORMAL}\n"
                    "Please ensure that you're in the VPN and the werk IDs server is "
                    "reachable when you create your next Werk.\n\n"
                )

        if not removed:
            raise RuntimeError(f"Could not find werk_id {werk_id} in any project.")

    def add_ids(self, werk_ids: Sequence["WerkId"]) -> None:
        """
        put a id into the stash
        """
        self.ids = sorted(set(self.ids).union(werk_id.id for werk_id in werk_ids))


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

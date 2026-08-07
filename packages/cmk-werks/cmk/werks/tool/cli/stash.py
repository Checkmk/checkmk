#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, Field

from .in_out_elements import TTY_NORMAL, TTY_RED
from .werk import WerkId


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
            raise RuntimeError("You have no Werk IDs in your stash.") from e

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


class LegacyStash(BaseModel):
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
                "You have no Werk IDs. Please run 'werk init' to switch to the new reservation "
                "mechanism, which reserves werk IDs on the fly during 'werk new'."
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

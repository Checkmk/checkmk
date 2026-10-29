#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What the GUI says the names of map links mean, without a GUI."""

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet

from cmk.maps.backend.core.auth import LinkTarget
from cmk.maps.backend.schemas.map import MapConfig


class FakeLinkGui:
    """Answers from ``sees``: per (user, name), the owner and config of the map they see.

    Without ``sees``, a name means the map of that user the daemon holds.
    """

    def __init__(self, sees: Mapping[tuple[str, str], tuple[str, MapConfig]] | None = None) -> None:
        self._sees = sees
        self.asked: list[tuple[str, list[str]]] = []
        self.held: list[AbstractSet[tuple[str, str]]] = []

    async def link_targets(
        self,
        as_user: str,
        names: Sequence[str],
        held: AbstractSet[tuple[str, str]],
        *,
        now: float,  # noqa: ARG002
    ) -> dict[str, LinkTarget]:
        self.asked.append((as_user, list(names)))
        self.held.append(held)
        if self._sees is None:
            return {name: LinkTarget(as_user) for name in names if (as_user, name) in held}
        targets = {}
        for name in names:
            if (seen := self._sees.get((as_user, name))) is not None:
                owner, cfg = seen
                targets[name] = LinkTarget(owner, None if (owner, name) in held else cfg)
        return targets

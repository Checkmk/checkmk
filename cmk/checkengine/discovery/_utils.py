#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
from collections.abc import Hashable, Iterable, Sequence
from typing import Final, Generic, Literal, Protocol, TypeVar

__all__ = ["DiscoveryMode", "QualifiedDiscovery"]


class DiscoveryMode(enum.Enum):
    # NOTE: the values 0-3 are used in WATO rules and must not be changed!
    NEW = 0
    REMOVE = 1
    FIXALL = 2
    REFRESH = 3
    ONLY_HOST_LABELS = 4
    FALLBACK = 5  # not sure why this could happen

    @classmethod
    def _missing_(cls, value: object) -> "DiscoveryMode":
        return cls.FALLBACK

    @classmethod
    def from_str(cls, value: str) -> "DiscoveryMode":
        # NOTE: 'only-host-labels' is sent by an automation call, so we need to deal with that.
        return cls[value.upper().replace("-", "_")]


class _Discoverable(Protocol):
    """
    Required interface for a qualified discovery.

    For discovered things (e.g. host labels, services) we need to decide
    wether things are new, old, vanished, or *changed*.
    Currently the "changed" is WIP.

    Anyway: we need a proper distiction between being the same entity and
    comparing equal.
    """

    def id(self) -> Hashable:
        ...

    # tbd: def comperator(self) -> object:
    #    ...


_DiscoveredItem = TypeVar("_DiscoveredItem", bound=_Discoverable)


class QualifiedDiscovery(Generic[_DiscoveredItem]):
    """Classify items into "new", "old" and "vanished" ones."""

    def __init__(
        self,
        *,
        preexisting: Sequence[_DiscoveredItem],
        current: Sequence[_DiscoveredItem],
    ) -> None:
        current_dict = {v.id(): v for v in current}
        preexisting_dict = {v.id(): v for v in preexisting}

        self.vanished: Final = [v for k, v in preexisting_dict.items() if k not in current_dict]
        self.old: Final = [v for k, v in preexisting_dict.items() if k in current_dict]
        self.new: Final = [v for k, v in current_dict.items() if k not in preexisting_dict]
        self.present: Final = self.old + self.new

    @classmethod
    def empty(cls) -> "QualifiedDiscovery":
        """create an empty instance"""
        return cls(preexisting=(), current=())

    def chain_with_qualifier(
        self,
    ) -> Iterable[tuple[Literal["vanished", "old", "new"], _DiscoveredItem]]:
        yield from (("vanished", value) for value in self.vanished)
        yield from (("old", value) for value in self.old)
        yield from (("new", value) for value in self.new)

    def kept(self) -> Sequence[_DiscoveredItem]:
        # TODO (mo): Clean this up, the logic is all backwards:
        # It seems we always keep the vanished ones here.
        # However: If we do not load the existing ones, nothing will be classified as 'vanished',
        # and the ones that *are* in fact vanished are dropped silently.
        return self.vanished + self.present

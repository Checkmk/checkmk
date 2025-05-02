#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import enum
import json
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Final, Generic, Literal, Protocol, Self, TypedDict, TypeVar

__all__ = ["DiscoveryMode", "QualifiedDiscovery", "DiscoverySettings"]


class DiscoverySettingFlags(TypedDict):
    add_new_services: bool
    remove_vanished_services: bool
    update_host_labels: bool
    update_changed_service_labels: bool
    update_changed_service_parameters: bool


DiscoveryValueSpecModel = tuple[Literal["update_everything", "custom"], DiscoverySettingFlags]


@dataclass(frozen=True)
class DiscoverySettings:
    update_host_labels: bool
    add_new_services: bool
    remove_vanished_services: bool
    update_changed_service_labels: bool
    update_changed_service_parameters: bool

    @classmethod
    def from_discovery_mode(cls, mode: DiscoveryMode) -> Self:
        return cls(
            update_host_labels=mode is not DiscoveryMode.REMOVE,
            add_new_services=mode
            in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH),
            remove_vanished_services=mode in (DiscoveryMode.REMOVE, DiscoveryMode.FIXALL),
            update_changed_service_labels=mode is DiscoveryMode.REFRESH,
            update_changed_service_parameters=mode is DiscoveryMode.REFRESH,
        )

    @classmethod
    def from_vs(cls, mode: DiscoveryValueSpecModel | None) -> Self:
        if mode is None:
            return cls(
                update_host_labels=False,
                add_new_services=False,
                remove_vanished_services=False,
                update_changed_service_labels=False,
                update_changed_service_parameters=False,
            )

        _ident, flags = mode
        return cls(
            update_host_labels=flags["update_host_labels"],
            add_new_services=flags["add_new_services"],
            remove_vanished_services=flags["remove_vanished_services"],
            update_changed_service_labels=flags["update_changed_service_labels"],
            update_changed_service_parameters=flags["update_changed_service_parameters"],
        )

    def to_automation_arg(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_automation_arg(cls, mode: str) -> DiscoverySettings:
        raw = json.loads(mode)
        # 2.3 format misses some keys.
        return cls(
            update_host_labels=raw.get("update_host_labels", False),
            add_new_services=raw.get("add_new_services", False),
            remove_vanished_services=raw.get("remove_vanished_services", False),
            update_changed_service_labels=raw.get("update_changed_service_labels", False),
            update_changed_service_parameters=raw.get("update_changed_service_parameters", False),
        )


class DiscoveryMode(enum.Enum):
    # NOTE: the values 0-3 are used in WATO rules and must not be changed!
    NEW = 0
    REMOVE = 1
    FIXALL = 2
    REFRESH = 3
    ONLY_HOST_LABELS = 4
    FALLBACK = 5  # not sure why this could happen

    @classmethod
    def _missing_(cls, value: object) -> DiscoveryMode:
        return cls.FALLBACK

    @classmethod
    def from_str(cls, value: str) -> DiscoveryMode:
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

    def id(self) -> Hashable: ...

    def comparator(self) -> object: ...


_DiscoveredItem = TypeVar("_DiscoveredItem", bound=_Discoverable)


@dataclasses.dataclass
class DiscoveredItem(Generic[_DiscoveredItem]):
    previous: _DiscoveredItem | None
    new: _DiscoveredItem | None
    older: _DiscoveredItem = dataclasses.field(init=False)
    newer: _DiscoveredItem = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        older = self.new if self.previous is None else self.previous
        newer = self.previous if self.new is None else self.new
        if older is None or newer is None:
            raise ValueError("Either 'previous' or 'new' must be set.")
        self.older = older
        self.newer = newer


class QualifiedDiscovery(Generic[_DiscoveredItem]):
    """Classify items into "new", "unchanged", "changed", and "vanished" ones."""

    def __init__(
        self,
        *,
        preexisting: Sequence[_DiscoveredItem],
        current: Sequence[_DiscoveredItem],
    ) -> None:
        self.preexisting: Final = preexisting
        self.current: Final = current

        current_dict = {v.id(): v for v in current}
        preexisting_dict = {v.id(): v for v in preexisting}

        self._vanished: Final = [
            DiscoveredItem(previous=v, new=None)
            for k, v in preexisting_dict.items()
            if k not in current_dict
        ]
        self._new: Final = [
            DiscoveredItem(previous=None, new=v)
            for k, v in current_dict.items()
            if k not in preexisting_dict
        ]
        self.changed: Final = [
            DiscoveredItem(previous=v, new=current_dict[k])
            for k, v in preexisting_dict.items()
            if k in current_dict and v.comparator() != current_dict[k].comparator()
        ]
        self.unchanged: Final = [
            DiscoveredItem(previous=v, new=v)
            for k, v in current_dict.items()
            if k in preexisting_dict and v.comparator() == preexisting_dict[k].comparator()
        ]
        self._old: Final = self.changed + self.unchanged

    @classmethod
    def empty(cls) -> QualifiedDiscovery:
        """create an empty instance"""
        return cls(preexisting=(), current=())

    @property
    def vanished(self) -> list[_DiscoveredItem]:
        return [item.previous for item in self._vanished if item.previous is not None]

    @property
    def old(self) -> list[_DiscoveredItem]:
        return [item.previous for item in self._old if item.previous is not None]

    @property
    def new(self) -> list[_DiscoveredItem]:
        return [item.new for item in self._new if item.new is not None]

    @property
    def present(self) -> list[_DiscoveredItem]:
        # not quite like 'current'!
        return self.old + self.new

    def chain_with_transition(
        self,
    ) -> Iterable[
        tuple[Literal["vanished", "unchanged", "changed", "new"], DiscoveredItem[_DiscoveredItem]]
    ]:
        yield from (("vanished", value) for value in self._vanished)
        yield from (("unchanged", value) for value in self.unchanged)
        yield from (("changed", value) for value in self.changed)
        yield from (("new", value) for value in self._new)

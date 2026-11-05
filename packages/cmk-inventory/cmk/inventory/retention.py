#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, TypedDict

from .filtering import make_filter_func
from .raw_paths import parse_visible_raw_path
from .trees import (
    ImmutableTree,
    MutableTree,
    RetentionInterval,
    SDKey,
    SDPath,
)


class _RawIntervalFromConfigMandatory(TypedDict):
    interval: int
    visible_raw_path: str


class RawIntervalFromConfig(_RawIntervalFromConfigMandatory, total=False):
    attributes: Literal["all"] | tuple[str, list[str]]
    columns: Literal["all"] | tuple[str, list[str]]


@dataclass(frozen=True)
class _SDRetentionFilterChoice:
    choice: Literal["nothing", "all"] | Sequence[SDKey]
    cache_info: tuple[int, int]


@dataclass(frozen=True, kw_only=True)
class SDRetentionFilterChoices:
    path: SDPath
    interval: int
    _pairs: list[_SDRetentionFilterChoice] = field(default_factory=list)
    _columns: list[_SDRetentionFilterChoice] = field(default_factory=list)

    @property
    def pairs(self) -> Sequence[_SDRetentionFilterChoice]:
        return self._pairs

    @property
    def columns(self) -> Sequence[_SDRetentionFilterChoice]:
        return self._columns

    def add_pairs_choice(
        self, choice: Literal["nothing", "all"] | Sequence[SDKey], cache_info: tuple[int, int]
    ) -> None:
        self._pairs.append(_SDRetentionFilterChoice(choice, cache_info))

    def add_columns_choice(
        self, choice: Literal["nothing", "all"] | Sequence[SDKey], cache_info: tuple[int, int]
    ) -> None:
        self._columns.append(_SDRetentionFilterChoice(choice, cache_info))


def update_tree(
    tree: MutableTree,
    *,
    now: int,
    previous_tree: ImmutableTree,
    choices: SDRetentionFilterChoices,
) -> None:
    for c in choices.pairs:
        tree.update_attributes(
            path=choices.path,
            now=now,
            previous_tree=previous_tree,
            filter_func=make_filter_func(c.choice),
            retention_interval=RetentionInterval.from_config(*c.cache_info, choices.interval),
        )
    for c in choices.columns:
        tree.update_table(
            path=choices.path,
            now=now,
            previous_tree=previous_tree,
            filter_func=make_filter_func(c.choice),
            retention_interval=RetentionInterval.from_config(*c.cache_info, choices.interval),
        )


def _parse_choice(
    raw_choice: Literal["all"] | tuple[str, list[str]],
) -> Sequence[SDKey] | Literal["all"]:
    return [SDKey(k) for k in raw_choice[-1]] if isinstance(raw_choice, tuple) else raw_choice


def make_retention_filter_choices(
    *,
    now: int,
    raw_intervals_from_config: Sequence[RawIntervalFromConfig],
    pairs_cache_info: Mapping[SDPath, tuple[int, int] | None],
    columns_cache_info: Mapping[SDPath, tuple[int, int] | None],
) -> Sequence[SDRetentionFilterChoices]:
    def cache_info(
        by_path: Mapping[SDPath, tuple[int, int] | None], path: SDPath
    ) -> tuple[int, int]:
        return (now, 0) if (ci := by_path.get(path)) is None else ci

    choices_by_path: dict[SDPath, SDRetentionFilterChoices] = {}
    for entry in raw_intervals_from_config:
        path = parse_visible_raw_path(entry["visible_raw_path"])
        choices = choices_by_path.setdefault(
            path, SDRetentionFilterChoices(path=path, interval=entry["interval"])
        )
        if attributes := entry.get("attributes"):
            choices.add_pairs_choice(
                choice=_parse_choice(attributes),
                cache_info=cache_info(pairs_cache_info, path),
            )
        elif columns := entry.get("columns"):
            choices.add_columns_choice(
                choice=_parse_choice(columns),
                cache_info=cache_info(columns_cache_info, path),
            )
    return list(choices_by_path.values())

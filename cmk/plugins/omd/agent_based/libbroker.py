#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
import json
from collections import defaultdict
from collections.abc import Generator, Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import groupby
from typing import Any, Callable, cast, Generic, TypeVar

from cmk.agent_based.v2 import StringTable


@dataclass(frozen=True)
class BrokerStatus:
    memory: int


@dataclass(frozen=True)
class Shovel:
    name: str
    state: str


@dataclass(frozen=True)
class Queue:
    vhost: str
    name: str
    messages: int


SectionQueues = Mapping[str, Sequence[Queue]]
SectionStatus = Mapping[str, BrokerStatus]
SectionShovels = Mapping[str, Sequence[Shovel]]
_Section = TypeVar("_Section", bound=Mapping[str, Any])
_S = TypeVar("_S", bound=Queue | BrokerStatus | Shovel)
SectionItem = tuple[str, _S]


_NODE_NAME_PREFIX = "rabbit-"
_NODE_NAME_SUFFIX = "@localhost"


def node_to_site(node_name: str) -> str:
    if not node_name.startswith(_NODE_NAME_PREFIX) or not node_name.endswith(_NODE_NAME_SUFFIX):
        raise ValueError(f"Invalid node name: {node_name}")
    return node_name.removeprefix(_NODE_NAME_PREFIX).removesuffix(_NODE_NAME_SUFFIX)


class MKRabbitMQError(Exception): ...


class Parser(Generic[_Section]):
    def __init__(self, callback: Callable[[dict[str, Any]], SectionItem], aggregate: bool) -> None:
        self._aggregate = aggregate
        self._callback = callback

    def _init_data_structure(self) -> dict[str, _Section | list[_Section]]:
        return defaultdict(list) if self._aggregate else {}

    def _aggregate_data_structure(self, sections: Iterable[SectionItem]) -> _Section:
        key_func = lambda k: k[0]
        return cast(
            _Section,
            {
                key: list(i[1] for i in items)
                for key, items in groupby(sorted(sections, key=key_func), key=key_func)
            },
        )

    def _parse(self, string_table: StringTable) -> Generator[SectionItem, None, None]:
        for (word,) in string_table:
            parsed_word = json.loads(word)
            if isinstance(parsed_word, dict) and "error" in parsed_word:
                raise MKRabbitMQError(parsed_word["error"])

            for node in parsed_word:
                yield self._callback(node)

    def __call__(self, string_table: StringTable) -> _Section | None:
        iterator = self._parse(string_table)
        try:
            if self._aggregate:
                return self._aggregate_data_structure(iterator)

            return cast(_Section, {key: value for key, value in iterator})
        except MKRabbitMQError:
            return None

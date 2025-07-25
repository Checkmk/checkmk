#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, TypedDict

# NOTE: intentionally not using the `type` syntax because it's not possible to use
# `typing.get_args` to dynamically check if string is type at runtime.
Provider = Literal["setup", "monitoring"]
SortType = Literal["alphabetic", "weighted_index"]


class UnifiedSearchResultItemSerialized(TypedDict):
    title: str
    url: str
    topic: str
    provider: Provider
    context: str


@dataclass(frozen=True, kw_only=True, order=True)
class UnifiedSearchResultItem:
    title: str
    url: str
    topic: str
    provider: Provider
    context: str = ""

    def serialize(self) -> UnifiedSearchResultItemSerialized:
        return {
            "title": self.title,
            "url": self.url,
            "topic": self.topic,
            "provider": self.provider,
            "context": self.context,
        }


class UnifiedSearchResultCountsSerialized(TypedDict):
    total: int
    setup: int
    monitoring: int


@dataclass(frozen=True, kw_only=True)
class UnifiedSearchResultCounts:
    total: int
    setup: int
    monitoring: int

    def serialize(self) -> UnifiedSearchResultCountsSerialized:
        return {
            "total": self.total,
            "setup": self.setup,
            "monitoring": self.monitoring,
        }


@dataclass(frozen=True, kw_only=True)
class UnifiedSearchResult:
    results: Iterable[UnifiedSearchResultItem]
    counts: UnifiedSearchResultCounts

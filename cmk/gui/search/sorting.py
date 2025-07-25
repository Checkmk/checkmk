#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from .type_defs import SortType, UnifiedSearchResultItem

type Sorter = Callable[[list[UnifiedSearchResultItem]], None]


def get_sorter(sort_type: SortType | None, query: str = "") -> Sorter:
    match sort_type:
        case "alphabetic":
            return _get_alphabetical_sorter
        case "weighted_index":
            return _get_weighted_index_sorter(query)
        case _:
            return _get_no_op_sorter


def _get_no_op_sorter(_: list[UnifiedSearchResultItem]) -> None:
    return None


def _get_alphabetical_sorter(items: list[UnifiedSearchResultItem]) -> None:
    items.sort(key=lambda item: item.title)


def _get_weighted_index_sorter(query: str) -> Sorter:
    def algorithm(item: UnifiedSearchResultItem) -> int:
        weighting = 5
        if (title_idx := item.title.lower().find(query)) >= 0:
            weighting = 1
            if len(item.title) == len(query):
                weighting = 0

            if title_idx > 0:
                weighting = 2
        else:
            title_idx = len(item.title)

        return weighting * title_idx

    def sorter(items: list[UnifiedSearchResultItem]) -> None:
        items.sort(key=lambda item: algorithm(item))

    return sorter

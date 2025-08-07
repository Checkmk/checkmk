#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
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


# NOTE: in the future, we want to support matching on different forms of a word.
#
# For example, the query "organize" should also match "organizes" and "organizing", or
# "democracy" to its derivations: "democratic" and "democratization". In traditional NLP,
# this was done with lemmatization, and recently, vector databases have proven to be an
# even more robust solution.
#
# However, to support this in Checkmk, it would require introducing new dependencies,
# multi-language support, and for the latter, architectural changes. So for now, this
# is out-of-scope.
def _get_weighted_index_sorter(query: str) -> Sorter:
    query_ = query.lower()
    topic_ranking_map = {topic: rank for rank, topic in enumerate(_TOPIC_RANKING)}
    unranked_topic = max(topic_ranking_map.values()) + 1

    def algorithm(item: UnifiedSearchResultItem) -> tuple[_MatchRank, int, str]:
        title_ = item.title.lower()
        topic_ = item.topic.lower()

        if query_ == title_:
            match_rank = _MatchRank.EXACT_TITLE
        elif f"({query_})" in title_:
            match_rank = _MatchRank.EXACT_TITLE_IN_PARENTHESES
        elif title_.startswith(query_):
            match_rank = _MatchRank.TITLE_STARTS_WITH_QUERY
        elif is_deprecated_result_item(title_, topic_):
            match_rank = _MatchRank.DEPRECATED_RESULT_ITEM
        else:
            match_rank = _MatchRank.DEFAULT_RANK

        topic_rank = topic_ranking_map.get(topic_, unranked_topic)

        return match_rank, topic_rank, item.title

    def sorter(items: list[UnifiedSearchResultItem]) -> None:
        items.sort(key=algorithm)

    return sorter


# TODO: move this out of the code; it 't belongs somewhere where it's easy to adjust.
_TOPIC_RANKING = (
    "setup",
    "monitor",
    "host monitoring rules",
    "notification parameter",
    "service monitoring rules",
    "global settings",
    "vm, cloud, container",
    "enforced services",
)


class _MatchRank(enum.IntEnum):
    EXACT_TITLE = 0
    EXACT_TITLE_IN_PARENTHESES = 1
    TITLE_STARTS_WITH_QUERY = 2
    DEFAULT_RANK = 3
    DEPRECATED_RESULT_ITEM = 4


# TODO: once metadata is factored out of code, introduce a "deprecated" attribute to result item.
def is_deprecated_result_item(title: str, topic: str) -> bool:
    if title.startswith("push notifications") and topic == "service monitoring rules":
        return True
    return False

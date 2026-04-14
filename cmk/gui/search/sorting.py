#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Callable

from cmk.gui.i18n import _
from cmk.shared_typing.unified_search import SortType, UnifiedSearchResultItem

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

    def algorithm(item: UnifiedSearchResultItem) -> tuple[int, _MatchRank, bool, str, str]:
        title_ = item.title.lower()

        topic_rank = _get_topic_ranking(item.topic)
        title_match_rank = _get_title_match_rank(title_, query_)
        deprecation_rank = _get_deprecation_rank(title_)

        # TODO: try and figure out if we can improve shared typing to account for non-Optional str
        # type with a blank string as default (original behavior).
        return topic_rank, title_match_rank, deprecation_rank, item.title, item.context or ""

    def sorter(items: list[UnifiedSearchResultItem]) -> None:
        items.sort(key=algorithm)

    return sorter


def _get_topic_ranking(topic: str) -> int:
    # TODO: the topics ranking should not live in code.
    topics_to_promote = _get_topics_to_promote()
    topics_to_demote = _get_topics_to_demote()

    if topic in topics_to_promote:
        return topics_to_promote.index(topic)

    unranked_topic = len(topics_to_promote)

    if topic in topics_to_demote:
        return (unranked_topic + 1) + topics_to_demote.index(topic)

    return unranked_topic


def _get_topics_to_promote() -> tuple[str, ...]:
    return (
        # provider topics
        _("Setup"),
        _("Monitor"),
        # additional agent configuration
        _("HTTP, TCP, email, ..."),
        _("VM, cloud, container"),
        _("Other integrations"),
        _("Agent rules"),
        # common rule configuration
        _("Host monitoring rules"),
        _("Notification parameter"),
        _("Service monitoring rules"),
        _("Service discovery rules"),
    )


def _get_topics_to_demote() -> tuple[str, ...]:
    return (
        _("Global settings"),
        _("Enforced services"),
        _("Deprecated rule sets"),
    )


class _MatchRank(enum.IntEnum):
    EXACT_TITLE = 0
    EXACT_TITLE_IN_PARENTHESES = 1
    TITLE_STARTS_WITH_QUERY = 2
    TITLE_CONTAINS_QUERY = 3
    DEFAULT_RANK = 4


def _get_title_match_rank(title: str, query: str) -> _MatchRank:
    if query == title:
        return _MatchRank.EXACT_TITLE
    if f"({query})" in title:
        return _MatchRank.EXACT_TITLE_IN_PARENTHESES
    if title.startswith(query):
        return _MatchRank.TITLE_STARTS_WITH_QUERY
    if query in title:
        return _MatchRank.TITLE_CONTAINS_QUERY
    return _MatchRank.DEFAULT_RANK


def _get_deprecation_rank(title: str) -> bool:
    # TODO: once metadata is factored out of code, introduce a "deprecated" attribute.
    # NOTE: need to check for both translated and untranslated patterns since some titles are
    # don't have translations.
    return any(pattern in title for pattern in ("(deprecated)", _("(deprecated)")))

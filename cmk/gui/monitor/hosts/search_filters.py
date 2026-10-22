#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Turn a global search spec (see ``cmk.gui.search.spec``) into the All hosts filter tree

Each clause of the spec becomes one condition on the top level of the tree, so the column filters
show it. Labels and tags are the exception: a column filter shows only one condition per field, so
their clauses become a single "all_of" condition per field, which filters the same.
"""

from collections.abc import Sequence

from cmk.gui.i18n import _
from cmk.gui.search.spec import (
    HostAddress,
    HostAlias,
    HostLabel,
    HostName,
    HostTag,
    PrefixedSearch,
    Term,
)

from ._api._filters import (
    AndNode,
    FilterNode,
    LabelChoiceCondition,
    LabelField,
    StringCondition,
    StringField,
)


class UnsupportedSearchError(ValueError):
    """Raised when All hosts can't filter on a search spec."""


def host_search_filter(spec: PrefixedSearch) -> FilterNode:
    """The All hosts filter tree for the spec

    Raises:
        UnsupportedSearchError: if All hosts can't filter on the spec.
    """
    # A label or tag field stands in for its condition, built once all its pairs are known.
    conditions: list[FilterNode | LabelField] = []
    pairs: dict[LabelField, dict[str, None]] = {}
    for clause in spec.clauses:
        match clause:
            case [HostLabel(key=key, value=value)]:
                field: LabelField = "labels"
                pair = key if value is None else f"{key}:{value}"
            case [HostTag(group=str(group), tag=tag)]:
                field = "tags"
                pair = f"{group}:{tag}"
            case _:
                conditions.append(_condition(clause))
                continue
        if field not in pairs:
            conditions.append(field)
        # A dict, as the page rejects a pair given twice, e.g. "hl:os:linux hl:os:linux".
        pairs.setdefault(field, {})[pair] = None

    nodes = [
        LabelChoiceCondition(type="condition", field=node, op="all_of", value=list(pairs[node]))
        if isinstance(node, str)
        else node
        for node in conditions
    ]
    return nodes[0] if len(nodes) == 1 else AndNode(type="and", children=nodes)


def _condition(clause: Sequence[Term]) -> FilterNode:
    match clause:
        case [HostName(), *_]:
            return _contains("name", clause)
        case [HostAlias(), *_]:
            return _contains("alias", clause)
        case [HostAddress(), *_]:
            return _contains("address", clause)
        case [HostTag(tag=tag)]:
            raise UnsupportedSearchError(
                _('Please specify the tag group, e.g. "tg:criticality:%(tag)s".') % {"tag": tag}
            )
        case _:
            raise UnsupportedSearchError(
                _("All hosts can only be searched by host name, alias, address, label and tag.")
            )


def _contains(field: StringField, clause: Sequence[Term]) -> StringCondition:
    # The terms of a clause are or-ed. Unanchored, "a|b" matches the same as an "or" node, which
    # no column filter shows.
    patterns = [
        term.pattern for term in clause if isinstance(term, HostName | HostAlias | HostAddress)
    ]
    return StringCondition(type="condition", field=field, op="contains", value="|".join(patterns))

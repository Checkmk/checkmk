#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Build the links from legacy views to the new monitoring pages, and read on the page which
filters such a link could not take over."""

from collections import defaultdict
from collections.abc import Callable, Sequence, Set
from typing import Final

from cmk.gui.http import Request
from cmk.gui.log import logger
from cmk.gui.type_defs import FilterName, VisualContext

from ._filters import FilterJSON, get_top_level_nodes, has_any_value
from ._translate import ContextFilterTranslation

_UNAPPLIED_FILTERS_VAR: Final = "unapplied"

# The two bounds of a range, sorted. A column filter shows them together as one range.
_RANGE_OPS: Final = ("gte", "lte")

type FilterTitleLookup = Callable[[FilterName], str | None]
"""Looks up the title of a legacy filter, ``None`` for a name that is no legacy filter."""


def encode_unapplied_filters(unapplied: Sequence[FilterName]) -> list[tuple[str, str]]:
    """Encode the filters a link could not take over as URL variables. Return none if it took
    over all of them."""
    return [(_UNAPPLIED_FILTERS_VAR, ",".join(unapplied))] if unapplied else []


def read_unapplied_filter_titles(
    request: Request, look_up_title: FilterTitleLookup
) -> list[tuple[FilterName, str]]:
    """Read from the URL of ``request`` the filters a link could not take over, with their
    titles. Leave out a name that is no legacy filter: the page only ever names real filters,
    whatever the URL says."""
    return [
        (name, title)
        for name in dict.fromkeys((request.var(_UNAPPLIED_FILTERS_VAR) or "").split(","))
        if name and (title := look_up_title(name)) is not None
    ]


def build_column_filter_check(shown_conditions: Set[str]) -> Callable[[FilterJSON], bool]:
    """Build the check that a page whose column filters show ``shown_conditions``, as
    ``field:op``, can show every condition of a tree in them.

    Use it as ``PageFilterModel.accepts_shape`` for links, with the conditions the shared schema
    ``page_filter_condition.json`` names for the page. Any other condition, e.g. a "not", an "or" of
    labels or an operator the column filter of its field does not show, would hide rows without
    anything on the page showing why. ``translate_context`` then reports the legacy filter that
    added such a condition as not applied.

    Two rules of the frontend's filter components are not in the schema, and no test keeps them in
    step. A column filter shows one condition on its field, or the lower and upper bound of a
    range: this check copies that. A free-text filter shows ``one_of`` only with a single value:
    this check does not, as the legacy filters for contacts give one."""

    def can_show_in_columns(node: FilterJSON) -> bool:
        ops_by_field: defaultdict[str, list[str]] = defaultdict(list)
        for child in get_top_level_nodes(node):
            if not _is_condition(child):
                return False
            field, op = str(child.get("field")), str(child.get("op"))
            if f"{field}:{op}" not in shown_conditions:
                return False
            ops_by_field[field].append(op)
        return all(
            len(ops) == 1 or tuple(sorted(ops)) == _RANGE_OPS for ops in ops_by_field.values()
        )

    return can_show_in_columns


def _is_condition(node: object) -> bool:
    return isinstance(node, dict) and node.get("type") == "condition"


def build_link_url[N](
    context: VisualContext,
    translate: Callable[[VisualContext], ContextFilterTranslation[N]],
    build_url: Callable[[N | None, Sequence[FilterName]], str],
) -> str:
    """Build the URL of a new monitoring page that keeps the filters of a legacy view.

    ``translate`` turns the view's ``context`` into the page's filter, and ``build_url`` builds the
    URL from it. If either fails, build the URL without filters and report every filter that has a
    value as not applied. That way the legacy view still renders, and the page never shows more
    rows than asked for without saying so."""
    try:
        translation = translate(context)
        return build_url(translation.filter, translation.unapplied)
    except Exception:
        logger.exception("Could not take over the filters of a legacy view for a link")
        return build_url(None, [name for name, value in context.items() if has_any_value(value)])

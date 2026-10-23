#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The kinds of legacy filters, each reading the variables of one filter of the legacy visuals.

A kind is configured with the variables the legacy filter keeps its value in; the page field the
condition targets is given at translation time, so that every page shares the same definition of
a legacy filter.
"""

import re
from collections.abc import Callable, Mapping, Sequence

from cmk.gui.type_defs import FilterHTTPVariables

IGNORED_TRISTATE = "-1"

# The pages treat a trailing "*" as a prefix match, the legacy filters match it literally.
_WILDCARD = "*"

type FilterJSON = dict[str, object]


class UntranslatableFilterError(Exception):
    pass


# The condition on a page field that the variables of a legacy filter mean, None if they restrict
# nothing. Raises UntranslatableFilterError if a page cannot express it.
type LegacyFilter = Callable[[FilterHTTPVariables, str], FilterJSON | None]

# The site IDs the variables of a legacy site filter name, none if they restrict nothing. Raises
# UntranslatableFilterError for an ID no page can take.
type SiteIds = Callable[[FilterHTTPVariables], list[str]]


def text(var: str, *, negatable: bool = True) -> LegacyFilter:
    """A legacy regular expression filter ("~~"), negated by a "neg_" variable unless the legacy
    filter has none, in which case that variable is ignored. The pages' "contains" is the same
    case-insensitive match."""

    def translate_text(value: FilterHTTPVariables, field: str) -> FilterJSON | None:
        if not (pattern := value.get(var, "")):
            return None
        # Best effort: Livestatus matches with RE2, so a pattern only RE2 rejects (e.g. a
        # lookahead or a backreference) still passes here and fails in the query.
        try:
            re.compile(pattern)
        except re.error as exc:
            raise UntranslatableFilterError from exc
        return _negate_if(
            _condition(field, "contains", pattern), negatable and _negated(var, value)
        )

    return translate_text


def exact_text(var: str) -> LegacyFilter:
    """A legacy "=" filter, negated by a "neg_" variable. The pages offer no equality operator;
    an anchored, escaped expression is equivalent."""

    def translate_exact_text(value: FilterHTTPVariables, field: str) -> FilterJSON | None:
        if not (exact := value.get(var, "")):
            return None
        node = _condition(field, "matches", f"^{re.escape(exact)}$")
        return _negate_if(node, _negated(var, value))

    return translate_exact_text


def address(var: str) -> LegacyFilter:
    """A legacy address filter: an exact address, or a prefix of one."""

    def translate_address(value: FilterHTTPVariables, field: str) -> FilterJSON | None:
        if not (addr := value.get(var, "")):
            return None
        prefix = value.get(f"{var}_prefix") == "yes"
        return _condition(
            field, "matches", f"^{re.escape(addr)}" if prefix else f"^{re.escape(addr)}$"
        )

    return translate_address


def site_ids(var: str, *, separator: str | None = None) -> SiteIds:
    """The site IDs a legacy site filter names: a single site, or several separated by
    ``separator``."""

    def read_site_ids(value: FilterHTTPVariables) -> list[str]:
        sites = _names(value.get(var, ""), separator)
        # Unlike the text fields, the pages accept any site ID, which would match no site.
        if any("\n" in site_id for site_id in sites):
            raise UntranslatableFilterError
        return sites

    return read_site_ids


def site(ids: SiteIds) -> LegacyFilter:
    """A legacy site filter: the site is one of the IDs it names."""

    def translate_site(value: FilterHTTPVariables, field: str) -> FilterJSON | None:
        if not (sites := ids(value)):
            return None
        return _condition(field, "one_of", sites)

    return translate_site


def name_list(var: str, *, separator: str | None = "|") -> LegacyFilter:
    """A legacy filter for names, e.g. groups, of which an object has to have one: a single name,
    or several separated by ``separator``. Negated, it has none of them, as the legacy "!>=" lines
    joined by "And" mean."""

    def translate_name_list(value: FilterHTTPVariables, field: str) -> FilterJSON | None:
        raw = value.get(var, "")
        if not (names := _names(raw, separator)):
            # Nothing but separators names nothing: the legacy filter matches no object with it,
            # or, negated, every object, which is no filter.
            if raw.strip() and not _negated(var, value):
                raise UntranslatableFilterError
            return None
        node = _condition(field, "one_of", _literal(names))
        return _negate_if(node, _negated(var, value))

    return translate_name_list


def flag(var: str) -> LegacyFilter:
    """A legacy tri-state filter: "1" for yes, "0" for no, anything else for either."""

    def translate_flag(value: FilterHTTPVariables, field: str) -> FilterJSON | None:
        if (pick := value.get(var, IGNORED_TRISTATE)) not in ("0", "1"):
            return None
        return _condition(field, "eq", pick == "1")

    return translate_flag


def state_choice(states: Mapping[str, str]) -> LegacyFilter:
    """Legacy state checkboxes, one variable per state. None or all of them checked means no
    filter."""

    def translate_state_choice(value: FilterHTTPVariables, field: str) -> FilterJSON | None:
        picked = [state for var, state in states.items() if value.get(var)]
        if not picked or len(picked) == len(states):
            return None
        return _condition(field, "one_of", picked)

    return translate_state_choice


def number_range(ident: str) -> LegacyFilter:
    """A legacy range filter with "_from" and "_until" bounds, each optional."""

    def translate_number_range(value: FilterHTTPVariables, field: str) -> FilterJSON | None:
        return all_of(
            [
                _condition(field, op, bound)
                for op, suffix in (("gte", "_from"), ("lte", "_until"))
                if (bound := _bound(value.get(f"{ident}{suffix}", ""))) is not None
            ]
        )

    return translate_number_range


def all_of(nodes: Sequence[FilterJSON]) -> FilterJSON | None:
    if len(nodes) < 2:
        return nodes[0] if nodes else None
    return {"type": "and", "children": list(nodes)}


def _bound(number: str) -> int | None:
    if not number:
        return None
    try:
        return int(number)
    except ValueError as exc:
        raise UntranslatableFilterError from exc


def _negated(var: str, value: FilterHTTPVariables) -> bool:
    return bool(value.get(f"neg_{var}"))


def _names(raw: str, separator: str | None) -> list[str]:
    if not (raw := raw.strip()):
        return []
    return [name for name in dict.fromkeys(raw.split(separator) if separator else [raw]) if name]


def _condition(field: str, op: str, value: object) -> FilterJSON:
    return {"type": "condition", "field": field, "op": op, "value": value}


def _literal(names: Sequence[str]) -> list[str]:
    if any(name.endswith(_WILDCARD) for name in names):
        raise UntranslatableFilterError
    return list(names)


def _negate_if(node: FilterJSON, negate: bool) -> FilterJSON:
    return {"type": "not", "child": node} if negate else node

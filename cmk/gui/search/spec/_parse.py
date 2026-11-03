#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Callable, Sequence
from typing import get_args, TypeIs

from cmk.gui.i18n import _

from ._terms import (
    HostAddress,
    HostAlias,
    HostFolder,
    HostGroup,
    HostLabel,
    HostName,
    HostTag,
    PrefixedSearch,
    SearchSpec,
    ServiceFolder,
    ServiceGroup,
    ServiceLabel,
    ServiceName,
    ServiceState,
    ServiceStateName,
    Term,
    UnprefixedSearch,
)


class SearchParseError(ValueError):
    """Raised when a query cannot be turned into a search spec."""


# Repeating these narrows the search instead of broadening it, e.g. tg:prod tg:linux.
_AND_COMBINED = (HostTag, HostLabel, ServiceLabel)

# One or two lower-case letters, the shape of all prefixes, followed by ":" at the start of the
# query or after whitespace. Longer words like "note:" are part of the value.
_PREFIX = re.compile(r"(?:^|(?<=\s))([a-z]{1,2}):")

# Their values start with a key, which may look like a prefix, e.g. "hl: os:linux".
_KEY_VALUE_PREFIXES = frozenset({"hl", "sl", "tg"})

# Control characters and the line breaks of str.splitlines(), which count as spaces. "\r\n" is one.
_CONTROL_CHARS = re.compile(r"\r\n|[\x00-\x1f\x7f\x85\u2028\u2029]")

# Livestatus uses re2, which does not support look-arounds. Same check as validate_regex in
# cmk.gui.utils.regex, which depends on the page and can't be used here.
_LOOKAROUND = re.compile(r"\((\?!|\?=|\?<)")


def parse(query: str) -> SearchSpec:
    """Turn a global search query into a search spec

    Raises:
        SearchParseError: if the query is empty or invalid.
    """
    # The search box has a single line, line breaks and other control characters can only come
    # from a hand-made URL.
    query = _CONTROL_CHARS.sub(" ", query)
    if not query.strip():
        raise SearchParseError(_("Please enter a search term."))

    if not (prefixes := _find_prefixes(query)):
        text = query.strip()
        return UnprefixedSearch(text=text, pattern=_regex(text))

    if leading := query[: prefixes[0].start()].strip():
        raise SearchParseError(
            _('The text "%(text)s" is not preceded by a search prefix such as "h:".')
            % {"text": leading}
        )

    clauses: list[list[Term]] = []
    or_clauses: dict[type[Term], list[Term]] = {}
    for match, end in zip(prefixes, [m.start() for m in prefixes[1:]] + [len(query)]):
        for term in _parse_term(match.group(1), query[match.end() : end].strip()):
            if isinstance(term, _AND_COMBINED):
                clauses.append([term])
            elif (clause := or_clauses.get(type(term))) is not None:
                clause.append(term)
            else:
                clause = or_clauses[type(term)] = [term]
                clauses.append(clause)

    return PrefixedSearch(clauses=tuple(tuple(clause) for clause in clauses))


def _find_prefixes(query: str) -> list[re.Match[str]]:
    prefixes = []
    pos = 0
    while match := _PREFIX.search(query, pos):
        prefixes.append(match)
        pos = match.end()
        if match.group(1) in _KEY_VALUE_PREFIXES:
            # Continue after the first character of the value, so its key is not taken for a prefix.
            pos = len(query) - len(query[pos:].lstrip()) + 1
    return prefixes


def _parse_term(prefix: str, value: str) -> Sequence[Term]:
    if (parse_term := _TERM_PARSERS.get(prefix)) is None:
        raise SearchParseError(_('Unknown search prefix "%(prefix)s:".') % {"prefix": prefix})
    if not value:
        raise SearchParseError(
            _('The search prefix "%(prefix)s:" needs a value.') % {"prefix": prefix}
        )
    return parse_term(value)


def _regex(value: str) -> str:
    # Like the dropdown (sanitize_regex in the legacy quicksearch), so both find the same.
    pattern = value.replace("*", ".*")
    try:
        re.compile(pattern)
    except re.error as e:
        raise SearchParseError(
            _('"%(value)s" is not a valid regular expression.') % {"value": value}
        ) from e
    if _LOOKAROUND.search(pattern):
        raise SearchParseError(
            _('"%(value)s" uses a look-around, which is not supported.') % {"value": value}
        )
    return pattern


def _folder(value: str) -> str:
    if not (path := value.strip("/")):
        raise SearchParseError(_('"%(value)s" is not a folder path.') % {"value": value})
    return path


def _group(value: str) -> str:
    _reject_bare_wildcard(value, value, example="linux*")
    return value


def _key_value(value: str) -> tuple[str, str | None]:
    key, sep, label_value = (part.strip() for part in value.partition(":"))
    if not sep and key.endswith("*"):
        _reject_bare_wildcard(value, key, example="cmk/aws*")
        return key, None
    if not key or not label_value:
        raise SearchParseError(
            _(
                '"%(value)s" is not a label. Labels are given as "key:value", e.g. "os:linux",'
                ' or as a key prefix, e.g. "cmk/aws*".'
            )
            % {"value": value}
        )
    _reject_wildcard_key(value, key)
    return key, label_value


def _host_tag(value: str) -> HostTag:
    group, sep, tag = (part.strip() for part in value.partition(":"))
    if not sep:
        _reject_bare_wildcard(value, value, example="lin*")
        return HostTag(group=None, tag=value)
    if not group or not tag:
        raise SearchParseError(
            _('"%(value)s" is not a host tag. Tags are given as "tag" or "group:tag".')
            % {"value": value}
        )
    _reject_wildcard_key(value, group)
    return HostTag(group=group, tag=tag)


def _reject_bare_wildcard(value: str, matched: str, *, example: str) -> None:
    # A group, label key or a tag without group can only be matched by prefix, not "any".
    if matched == "*":
        raise SearchParseError(
            _('"%(value)s": a "*" matches by prefix and needs text before it, e.g. "%(example)s".')
            % {"value": value, "example": example}
        )


def _reject_wildcard_key(value: str, key: str) -> None:
    # A "*" in a label key or tag group is literal, a lone one would only find a key named "*".
    if key == "*":
        raise SearchParseError(
            _(
                '"%(value)s": a "*" cannot stand for any label key or tag group. Please specify'
                ' one, e.g. "os:linux".'
            )
            % {"value": value}
        )


_SERVICE_STATES: tuple[ServiceStateName, ...] = get_args(ServiceStateName.__value__)


def _is_service_state(name: str) -> TypeIs[ServiceStateName]:
    return name in _SERVICE_STATES


def _service_states(value: str) -> Sequence[ServiceState]:
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1]
    states = []
    for name in dict.fromkeys(name.strip() for name in value.lower().split("|")):
        if not name:
            raise SearchParseError(
                _('The search prefix "st:" has an empty service state. Use one of: %(states)s.')
                % {"states": ", ".join(_SERVICE_STATES)}
            )
        if not _is_service_state(name):
            raise SearchParseError(
                _('Unknown service state "%(state)s". Use one of: %(states)s.')
                % {"state": name, "states": ", ".join(_SERVICE_STATES)}
            )
        states.append(ServiceState(state=name))
    return states


def prefix_of(term: Term) -> str:
    """The prefix ``term`` is given with, without the ``:``."""
    return _PREFIXES[type(term)]


_PREFIXES: dict[type[Term], str] = {
    HostName: "h",
    HostAlias: "al",
    HostAddress: "ad",
    HostGroup: "hg",
    HostLabel: "hl",
    HostTag: "tg",
    HostFolder: "hf",
    ServiceName: "s",
    ServiceGroup: "sg",
    ServiceState: "st",
    ServiceLabel: "sl",
    ServiceFolder: "sf",
}

_TERM_PARSERS: dict[str, Callable[[str], Sequence[Term]]] = {
    "h": lambda value: [HostName(pattern=_regex(value))],
    "al": lambda value: [HostAlias(pattern=_regex(value))],
    "ad": lambda value: [HostAddress(pattern=_regex(value))],
    "hg": lambda value: [HostGroup(name=_group(value))],
    "hl": lambda value: [HostLabel(*_key_value(value))],
    "tg": lambda value: [_host_tag(value)],
    "hf": lambda value: [HostFolder(path=_folder(value))],
    "s": lambda value: [ServiceName(pattern=_regex(value))],
    "sg": lambda value: [ServiceGroup(name=_group(value))],
    "st": _service_states,
    "sl": lambda value: [ServiceLabel(*_key_value(value))],
    "sf": lambda value: [ServiceFolder(path=_folder(value))],
}

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The translation of the host label filter repeats the logic with which the legacy filter encodes
its labels. This test keeps the two from drifting apart: for every combination of operators, the
translated filter selects a host if and only if the legacy filter does."""

import re
from collections.abc import Iterator
from itertools import chain, combinations, product

from cmk.gui.monitor.legacy_context import translate_context
from cmk.gui.type_defs import FilterHTTPVariables
from cmk.gui.utils.labels import (
    encode_label_groups_for_livestatus,
    parse_label_groups_from_http_vars,
)

from .testlib import ANY_PAGE, label_group_variables, LabelGroups

_OPERATORS = ("and", "or", "not")
_LABELS = ["a:1", "b:1", "c:1"]
_HOSTS = [
    frozenset(labels)
    for labels in chain.from_iterable(
        combinations(_LABELS, size) for size in range(len(_LABELS) + 1)
    )
]


def _selected_by_legacy_filter(variables: FilterHTTPVariables, host: frozenset[str]) -> bool:
    """Run the Livestatus lines of the legacy filter the way Livestatus does, as a stack machine."""
    groups = parse_label_groups_from_http_vars("host_labels", variables)
    stack: list[bool] = []
    for line in encode_label_groups_for_livestatus("labels", groups).splitlines():
        if match := re.fullmatch(r"Filter: labels = '(.*)' '(.*)'", line):
            stack.append(f"{match[1]}:{match[2]}" in host)
        elif line == "Negate:":
            stack.append(not stack.pop())
        elif match := re.fullmatch(r"(And|Or): (\d+)", line):
            operands = [stack.pop() for _ in range(int(match[2]))]
            stack.append(all(operands) if match[1] == "And" else any(operands))
    # Lines that are left over are connected by "And".
    return all(stack)


def _selected_by_tree(node: object, host: frozenset[str]) -> bool:
    match node:
        case None:
            return True
        case {"type": "and", "children": list(children)}:
            return all(_selected_by_tree(child, host) for child in children)
        case {"type": "or", "children": list(children)}:
            return any(_selected_by_tree(child, host) for child in children)
        case {"type": "not", "child": child}:
            return not _selected_by_tree(child, host)
        case {"type": "condition", "field": "labels", "op": "all_of", "value": list(labels)}:
            return all(label in host for label in labels)
        case _:
            raise ValueError(node)


def _selected_by_translation(variables: FilterHTTPVariables) -> set[frozenset[str]]:
    translation = translate_context({"host_labels": variables}, {"host_labels": "labels"}, ANY_PAGE)
    assert translation.unapplied == []
    return {host for host in _HOSTS if _selected_by_tree(translation.filter, host)}


def _selected_by_legacy(variables: FilterHTTPVariables) -> set[frozenset[str]]:
    return {host for host in _HOSTS if _selected_by_legacy_filter(variables, host)}


def _one_group() -> Iterator[LabelGroups]:
    """Every operator for each of one to three labels and for the group, with an empty label at
    each position or none."""
    for size in range(1, len(_LABELS) + 1):
        for empty_at in (None, *range(size + 1)):
            labels = list(_LABELS[:size])
            if empty_at is not None:
                labels.insert(empty_at, "")
            for group_operator in _OPERATORS:
                for operators in product(_OPERATORS, repeat=len(labels)):
                    yield [(group_operator, list(zip(operators, labels)))]


def _several_groups() -> Iterator[LabelGroups]:
    """Two and three groups, each of one of a few shapes of labels, with every operator for the
    groups."""
    shapes = [
        [("and", "a:1")],
        [("and", "a:1"), ("or", "b:1")],
        [("not", "c:1"), ("and", "a:1")],
        [("and", "")],
    ]
    for count in (2, 3):
        for group_labels in product(shapes, repeat=count):
            for operators in product(_OPERATORS, repeat=count):
                yield list(zip(operators, group_labels))


def test_host_label_filter_agrees_with_legacy_filter_for_all_operators() -> None:
    mismatches = []
    for groups in chain(_one_group(), _several_groups()):
        variables = label_group_variables(groups)
        translated, legacy = _selected_by_translation(variables), _selected_by_legacy(variables)
        if translated != legacy:
            # Only the hosts that just one of the filters selects, so that the cause is visible.
            mismatches.append((groups, translated ^ legacy))

    assert mismatches == []

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checks a Livestatus object filter being written the way Livestatus runs it."""

from collections.abc import Sequence
from typing import Final

from cmk.livestatus_client.expressions import (
    And,
    BinaryExpression,
    LiteralExpression,
    LIVESTATUS_OPERATORS,
    Not,
    NothingExpression,
    Or,
    QueryExpression,
)
from cmk.livestatus_client.tables import Hosts, Services
from cmk.livestatus_client.types import Column, Table

# Livestatus knows both; Checkmk's own list leaves them out.
_OPERATORS: Final = frozenset((*LIVESTATUS_OPERATORS, "=~", "!=~"))


def check_object_filter(object_filter: str, object_types: str | None) -> None:
    """Reject a filter Livestatus would refuse to run.

    ``And:``, ``Or:`` and ``Negate:`` must find the lines they combine, and each
    ``Filter:`` line must name a column and an operator of the queried table: the
    services table for a service filter, the hosts table otherwise. Only for a
    filter being written: the columns differ between Checkmk versions, and a
    stored map must still load. *object_filter* must have passed
    :func:`cmk.maps.shared.filters.normalize_object_filter`.
    """
    _filter_expression(
        object_filter.splitlines(),
        Services if object_types == "service" else Hosts,
    )


def _filter_expression(lines: Sequence[str], table: type[Table]) -> QueryExpression:
    """The filter as a Livestatus expression, built the way Livestatus stacks it."""
    stack: list[QueryExpression] = []
    for line in lines:
        header, _, argument = line.partition(":")
        argument = argument.strip()
        if header == "Filter":
            stack.append(_comparison(argument, table))
        elif header == "Negate":
            if not stack:
                raise ValueError("'Negate:' needs a line before it to negate")
            stack.append(Not(stack.pop()))
        elif (count := int(argument)) == 0:
            # True for And, false for Or; the tree has no node for either.
            stack.append(NothingExpression())
        elif count > len(stack):
            raise ValueError(f"'{header}: {count}' needs {count} lines before it to combine")
        else:
            combined = stack[-count:]
            del stack[-count:]
            stack.append((And if header == "And" else Or)(*combined))
    return And(*stack)


def _comparison(argument: str, table: type[Table]) -> BinaryExpression:
    column, operator, operand = (argument.split(maxsplit=2) + ["", ""])[:3]
    if not _is_column(table, column):
        raise ValueError(f"unknown column {column!r}")
    if operator not in _OPERATORS:
        raise ValueError(f"unknown operator {operator!r}")
    return BinaryExpression(LiteralExpression(column), LiteralExpression(operand), operator)


def _is_column(table: type[Table], column: str) -> bool:
    # Livestatus drops the table's prefix, so ``host_name`` is the hosts' ``name``.
    prefix = table.__tablename__.rstrip("s") + "_"
    while not isinstance(getattr(table, column, None), Column) and column.startswith(prefix):
        column = column.removeprefix(prefix)
    return isinstance(getattr(table, column, None), Column)

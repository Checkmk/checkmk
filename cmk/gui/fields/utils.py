#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="unreachable"

import typing
from collections.abc import Mapping
from typing import Any

from cmk.ccc.version import Edition
from cmk.gui.fields.base import BaseSchema as BaseSchema
from cmk.livestatus_client import tables
from cmk.livestatus_client.expressions import (
    And,
    BinaryExpression,
    LiteralExpression,
    LIVESTATUS_OPERATORS,
    Not,
    Or,
    QueryExpression,
    UnaryExpression,
)
from cmk.livestatus_client.types import Column, Table


def tree_to_expr(
    filter_dict: QueryExpression | typing.Mapping[str, Any], table: Any = None
) -> QueryExpression:
    """Turn a filter-dict into a QueryExpression.

    Examples:

        >>> tree_to_expr({'op': '=', 'left': 'hosts.name', 'right': 'example.com'})
        Filter(name = example.com)

        >>> tree_to_expr({'op': '!=', 'left': 'hosts.name', 'right': 'example.com'})
        Filter(name != example.com)

        >>> tree_to_expr({'op': '!=', 'left': 'name', 'right': 'example.com'}, 'hosts')
        Filter(name != example.com)

        >>> tree_to_expr({'op': 'and', \
                          'expr': [{'op': '=', 'left': 'hosts.name', 'right': 'example.com'}, \
                          {'op': '=', 'left': 'hosts.state', 'right': '0'}]})
        And(Filter(name = example.com), Filter(state = 0))

        >>> tree_to_expr({'op': 'or', \
                          'expr': [{'op': '=', 'left': 'hosts.name', 'right': 'example.com'}, \
                          {'op': '=', 'left': 'hosts.name', 'right': 'heute'}]})
        Or(Filter(name = example.com), Filter(name = heute))

        >>> tree_to_expr({'op': 'not', \
                          'expr': {'op': '=', 'left': 'hosts.name', 'right': 'example.com'}})
        Not(Filter(name = example.com))

        >>> tree_to_expr({'op': 'not', \
                          'expr': {'op': 'not', \
                                   'expr': {'op': '=', \
                                            'left': 'hosts.name', \
                                            'right': 'example.com'}}})
        Not(Not(Filter(name = example.com)))

        >>> from cmk.livestatus_client.tables import Hosts
        >>> tree_to_expr({'op': 'not', 'expr': Hosts.name == 'example.com'})
        Not(Filter(name = example.com))

        >>> tree_to_expr({'op': 'no_way', \
                          'expr': {'op': '=', 'left': 'hosts.name', 'right': 'example.com'}})
        Traceback (most recent call last):
        ...
        ValueError: Unknown operator: no_way

    Args:
        filter_dict:
            A filter-dict, which can either be persisted or passed over the wire.

        table:
            Optionally a table name. Only used when the columns are used in plain form
            (without table name prefixes).

    Returns:
        A valid LiveStatus query expression.

    Raises:
        ValueError: when unknown columns are queried

    """
    if not isinstance(filter_dict, Mapping):
        # FIXME
        #   Because of not having correct Python packages at the root-level, sometimes a
        #   locally defined class ends up having a relative dotted path, like for example
        #       <class 'expressions.BinaryExpression'>
        #   instead of
        #       <class 'cmk.utils.livestatus_helpers.expressions.BinaryExpression'>
        #   While these classes are actually the same, Python treats them distinct, so we can't
        #   just say `isinstance(filter_dict, BinaryExpression)` (or their super-type) here.
        return filter_dict
    op = filter_dict["op"]
    if op in LIVESTATUS_OPERATORS:
        left = filter_dict["left"]
        if "." in left:
            _table, column = left.split(".")
            if table is not None and _table_name(table) != _table:
                raise ValueError(
                    f"This field can only query table {_table_name(table)!r}. ({left})"
                )
        else:
            if table is None:
                raise ValueError("Missing table parameter.")
            _table = _table_name(table)
            column = left
        return BinaryExpression(
            _lookup_column(_table, column),
            LiteralExpression(filter_dict["right"]),
            op,
        )

    if op == "and":
        return And(*[tree_to_expr(expr, table) for expr in filter_dict["expr"]])

    if op == "or":
        return Or(*[tree_to_expr(expr, table) for expr in filter_dict["expr"]])

    if op == "not":
        return Not(tree_to_expr(filter_dict["expr"], table))

    raise ValueError(f"Unknown operator: {op}")


def _lookup_column(table_name: str | type[Table], column_name: str) -> UnaryExpression:
    if isinstance(table_name, str):
        table_class = getattr(tables, table_name.title())
    else:
        table_class = table_name
        table_name = table_class.__tablename__

    try:
        column: Column = getattr(table_class, column_name)
    except AttributeError as e:
        raise ValueError(f"Table {table_name!r} has no column {column_name!r}.") from e
    return column.expr


def _table_name(table: type[Table]) -> str:
    if isinstance(table, str):
        return table

    return table.__tablename__


def get_multiple_edition_description(editions: typing.Container[Edition]) -> str:
    """Get an *untranslated* description for multiple editions."""
    ordered_editions = tuple(
        edition for edition in Edition.__members__.values() if edition in editions
    )
    special_cases = {
        tuple(Edition.__members__.values()): "all",
        (
            Edition.COMMUNITY,
            Edition.PRO,
            Edition.ULTIMATE,
            Edition.ULTIMATEMT,
        ): "all self-hosted editions",
        (
            Edition.PRO,
            Edition.ULTIMATE,
            Edition.ULTIMATEMT,
            Edition.CLOUD,
        ): "all commercial editions",
    }
    if special_case := special_cases.get(ordered_editions):
        return special_case

    edition_titles = {
        Edition.COMMUNITY: "Community",
        Edition.PRO: "Pro",
        Edition.ULTIMATE: "Ultimate",
        Edition.ULTIMATEMT: "Ultimate with multi-tenancy",
        Edition.CLOUD: "Cloud",
    }
    return ", ".join(edition_titles[edition] for edition in ordered_editions)


def edition_field_description(
    description: str,
    supported_editions: set[Edition] | None = None,
    excluded_editions: set[Edition] | None = None,
    field_required: bool = False,
) -> str:
    """

    Example:
        >>> edition_field_description("This is a test description.", supported_editions={Edition.PRO}, field_required=True)
        '[Only in editions: Pro] This is a test description. This field is required for the following editions: Pro.'

        >>> edition_field_description("This is a test description.", supported_editions={Edition.PRO, Edition.ULTIMATE}, field_required=True)
        '[Only in editions: Pro, Ultimate] This is a test description. This field is required for the following editions: Pro, Ultimate.'

    """
    if supported_editions and excluded_editions:
        raise ValueError("supported_editions and excluded_editions are mutually exclusive.")

    if supported_editions:
        editions: typing.Container[Edition] = supported_editions
    elif excluded_editions:
        editions = [
            edition for edition in Edition.__members__.values() if edition not in excluded_editions
        ]
    else:
        raise ValueError("Either supported_editions or excluded_editions must be provided.")

    editions_string = get_multiple_edition_description(editions)
    description = f"[Only in editions: {editions_string}] {description}"

    if field_required:
        description += f" This field is required for the following editions: {editions_string}."
    return description

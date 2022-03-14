#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
from typing import Any, Dict, List, Literal, Optional, Type

from cmk.utils.livestatus_helpers.expressions import (
    BinaryExpression,
    BoolExpression,
    ListExpression,
    Not,
    NothingExpression,
    QueryExpression,
    ScalarExpression,
)

LivestatusType = Literal["string", "int", "float", "list", "dict", "time", "blob"]
ExpressionDict = Dict[str, Any]


class Table(abc.ABC):
    """Baseclass of all livestatus tables.

    This class doesn't do much, it just acts as a container for `Column` instances.
    """

    __tablename__: str

    @classmethod
    def __columns__(cls) -> List[str]:
        """Gives a list of all columns which are defined on the Table."""
        columns = []
        for key, value in cls.__dict__.items():
            if isinstance(value, Column):
                columns.append(key)
        return columns


class NoTable(Table):
    """Like a livestatus table, but not really.

    Can be used in place of an actual table, in order to not have to use `Optional` types when
    something is initialized only later.
    """

    @classmethod
    def __columns__(cls) -> List[str]:
        raise NotImplementedError("NoTable instances have no columns.")


class Column:
    """A representation of a livestatus column.

    This holds the name and type and can be used in comparisons to emit instances of
    `BinaryExpression`.

    The use of the type information can certainly be improved, but the most basic decisions (list
    or scalar) is being done already.

    """

    # I decided to implement this as a Descriptor in order to be able to
    # reference the Table from an actual Column instance and also preserve
    # the ability to tab-complete in various editors.
    # This means that the references will only ever be available after a Column
    # has been accessed via an attribute on the Table class. In terms of
    # implementation-complexity this solution wins though.
    def __init__(
        self,
        name: str,
        col_type: LivestatusType,
        description: Optional[str] = None,
    ):
        """A representation of a livestatus column.

        Args:
            name:
                The name of the column, as it is supposed to be adressed in livestatus. The
                attribute-name on the Table is not significant for query generation.

            col_type:
                One of livestatus' column types.

            description:
                The documentation for this column. The __doc__ attribute will be populated with
                this text.

        Examples:

            >>> class Hosts(Table):
            ...     __tablename__ = 'hosts'
            ...
            ...     name = Column('name', 'string', 'The host-name')

            >>> Hosts.name.table.__tablename__
            'hosts'

            >>> Hosts.name.contains('heute')
            Filter(name ~ heute)

        Returns:
            object:
        """
        self.name = name
        self.label_name: Optional[str] = None
        self.type: LivestatusType = col_type
        self.expr = ListExpression(name) if col_type == "list" else ScalarExpression(name)
        self.table: Type[Table] = NoTable

        self.__doc__ = description

    @property
    def full_name(self):
        # This needs to be a @property, due to the descriptor magic mentioned elsewhere.
        return f"{self.table.__tablename__}.{self.name}"

    def __str__(self):
        return self.name

    def __repr__(self):
        class_name = self.__class__.__name__
        return f"{class_name}({self.full_name}: {self.type})"

    @property
    def query_name(self) -> str:
        """This represents the name to be used in the Response.

        In case you want to use `iterate` to get a sequence of dicts, you can set the key within
        this dict by calling `label(label_name)`. The supplied name will be emitted here for use
        in response generation.

        Returns:
            The name to be used in the query response.
        """
        return self.label_name if self.label_name is not None else self.name

    def label(self, label_name: str) -> "Column":
        """Set the label for use in the response.

        Args:
            label_name:
                The name which the column should have in the response.

        Returns:
            A copy of this column, with the label set.

        """
        copy = Column(self.name, self.type, self.__doc__)
        copy.table = self.table
        copy.label_name = label_name
        return copy

    def __get__(self, obj, obj_type) -> "Column":
        # As we don't know on which Table this Column is located, we use
        # the descriptor protocol during attribute access to find out.
        if self.table is NoTable:
            self.table = obj_type

        return self

    def __eq__(self, other):
        return self.expr.__eq__(other)

    def __ne__(self, other):
        return self.expr.__ne__(other)

    def __lt__(self, other):
        return self.expr.__lt__(other)

    def __le__(self, other):
        return self.expr.__le__(other)

    def __gt__(self, other):
        return self.expr.__gt__(other)

    def __ge__(self, other):
        return self.expr.__ge__(other)

    def equals(self, other, ignore_case=False):
        return self.expr.equals(other, ignore_case=ignore_case)

    def contains(self, other, ignore_case=False):
        return self.expr.contains(other, ignore_case=ignore_case)

    def disparity(self, other, ignore_case=False):
        return self.expr.disparity(other, ignore_case=ignore_case)

    def op(self, op_str, other) -> BinaryExpression:
        return self.expr.op(op_str, other)

    def empty(self):
        return self.expr.empty()


def expr_to_tree(
    table: Type[Table],
    query_expr: QueryExpression,
) -> Optional[ExpressionDict]:
    """Transform the query-expression to a dict-tree.

    Examples:

        >>> from cmk.utils.livestatus_helpers.expressions import And
        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> expr_to_tree(Hosts, Not(And(Hosts.name == 'heute', Hosts.alias == 'heute')))
        {'op': 'not', 'expr': {'op': 'and', 'expr': [\
{'op': '=', 'left': 'hosts.name', 'right': 'heute'}, \
{'op': '=', 'left': 'hosts.alias', 'right': 'heute'}]}}

    Args:
        table:
        query_expr:

    Returns:
        A nested dictionary tree, which uniquely represents the given query-expression.

    """
    if isinstance(query_expr, BinaryExpression):
        return {
            "op": query_expr.operator,
            "left": getattr(table, query_expr.left.value).full_name,
            "right": query_expr.right.value,
        }

    if isinstance(query_expr, BoolExpression):
        return {
            "op": query_expr.__class__.__name__.lower(),
            "expr": [expr_to_tree(table, arg) for arg in query_expr.args],
        }

    if isinstance(query_expr, Not):
        return {"op": "not", "expr": expr_to_tree(table, query_expr.other)}

    if isinstance(query_expr, NothingExpression):
        return None

    raise ValueError(f"Unsupported expression: {query_expr!r}")

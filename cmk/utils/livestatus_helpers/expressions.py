#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Livestatus Query Expression System

This will generate Livestatus queries from an abstract representation. This has the advantage
that each query is type-checked and can be easily parametrized without having to resort to
string concatenation.

It's implementation is still a bit rudimentary but supports most necessary concepts already.

"""

import abc
from typing import Any, cast, List, Tuple

# TODO: column functions
# TODO: more tests

RenderIntermediary = List[Tuple[str, str]]

LIVESTATUS_OPERATORS = [
    "=",
    "<",
    ">",
    "<=",
    ">=",
    "~",
    "~~",
    "!=",
    "!<",
    "!>",
    "!<=",
    "!>=",
    "!~",
    "!~~",
]


class QueryExpression(abc.ABC):
    """Baseclass of all 'Filter:' expressions."""

    @abc.abstractmethod
    def render(self) -> RenderIntermediary:
        raise NotImplementedError()


class NothingExpression(QueryExpression):
    """A filter which does not do anything.

    This can be used in case of a do-nothing default filter.

    Note:
        This is like a type-checkable None, but doesn't solve all it's problems.
        It generates edge-cases elsewhere, see BoolExpression.render()

    >>> NothingExpression().render()
    []

    >>> And(NothingExpression(), NothingExpression()).render()
    []

    >>> And(And(NothingExpression()), NothingExpression()).render()
    []

    >>> And(LiteralExpression("foo") == LiteralExpression("bar"), NothingExpression()).render()
    [('Filter', 'foo = bar')]

    """

    def render(self) -> RenderIntermediary:
        return []


class UnaryExpression(abc.ABC):
    """Base class of all concrete single parts of BinaryExpression."""

    def __init__(self, value):
        self.value = value

    def op(self, operator: str, other: Any) -> "BinaryExpression":
        # TODO: typing
        if isinstance(other, (list, tuple)):
            other = LiteralExpression(" ".join(other))
        if not isinstance(other, UnaryExpression):
            other = LiteralExpression(other)
        return BinaryExpression(self, other, operator)

    def __repr__(self):
        return "<%s %s 0x%x>" % (self.__class__.__name__, self.value, id(self))

    @abc.abstractmethod
    def __eq__(self, other):
        raise NotImplementedError()

    def __lt__(self, other):
        return self.op("<", other)

    def __gt__(self, other):
        return self.op(">", other)

    def __le__(self, other):
        return self.op("<=", other)

    def __ge__(self, other):
        return self.op(">=", other)

    def __ne__(self, other):
        return Not(self.__eq__(other))

    @abc.abstractmethod
    def equals(self, other, ignore_case=False):
        raise NotImplementedError()

    @abc.abstractmethod
    def contains(self, other, ignore_case=False):
        raise NotImplementedError()

    @abc.abstractmethod
    def disparity(self, other, ignore_case=False):
        raise NotImplementedError()

    @abc.abstractmethod
    def empty(self):
        raise NotImplementedError()


class ScalarExpression(UnaryExpression):
    """

    >>> s = ScalarExpression("col")
    >>> s == 5
    Filter(col = 5)

    >>> s.contains("[abc]")
    Filter(col ~ [abc])

    = 	Equality 	Equality
    ~ 	Superset** 	Contains a character string as a regular expression.
    =~ 	Subset** 	Case-insensitive equality
    ~~ 	Contains at least one of the values** 	Contains a case-insensitive character string as a regular expression
    < 	Smaller than 	Lexicographically smaller than
    > 	Larger than 	Lexicographically larger than
    <= 	Smaller or equal 	Lexicographically smaller or equal
    >= 	Larger or equal 	Lexicographically larger or equal
    """

    def __eq__(self, other):
        return self.op("=", other)

    def equals(self, other, ignore_case=False):
        if ignore_case:
            return self.op("=~", other)

        return self.op("=", other)

    def contains(self, other, ignore_case=False):
        if ignore_case:
            return self.op("~~", other)

        return self.op("~", other)

    def empty(self):
        raise NotImplementedError("Not implemented for this type.")

    def disparity(self, other, ignore_case=False):
        raise NotImplementedError("Not implemented for this type.")


class ListExpression(UnaryExpression):
    """
    = 	Checks for empty lists*
    >= 	Equality
    < 	Disparity
    <= 	Case-insensitive equality
    > 	Case-insensitive disparity
    ~ 	The character string for a regular expression*
    ~~ 	The case-insensitive character string for a regular expression*

    >>> ListExpression("column").empty()
    Filter(column = )

    """

    def __eq__(self, other):
        return self.equals(other)

    def equals(self, other, ignore_case=False):
        if not other:
            # Check for empty list
            op = "="
        else:
            if ignore_case:
                # case-insensitive equality
                op = "<="
            else:
                # equality
                op = ">="
        return self.op(op, other)

    def disparity(self, other, ignore_case=False):
        if ignore_case:
            op = ">"
        else:
            op = "<"
        return self.op(op, other)

    def contains(self, other, ignore_case=False):
        return self.op("~~", other)

    def empty(self):
        return self.op("=", LiteralExpression(""))


class LiteralExpression(ScalarExpression):
    """A literal value to be rendered in a Filter

    Examples:

        >>> LiteralExpression("blah").render()
        [('', 'blah')]

      We make sure not to accidentally send query terminating newlines.

        >>> LiteralExpression("blah\\n\\n").render()
        [('', 'blah')]

    """

    def disparity(self, other, ignore_case=False):
        raise NotImplementedError("Not implemented for this type.")

    def empty(self):
        raise NotImplementedError("Not implemented for this type.")

    def render(self) -> RenderIntermediary:
        return [("", self.value.replace("\n", ""))]


LivestatusOperator = str


class BinaryExpression(QueryExpression):
    """Represents a comparison of some sort.

    Examples:

        >>> fexp = LiteralExpression("hurz") == LiteralExpression("blah")
        >>> fexp.render()
        [('Filter', 'hurz = blah')]

    """

    def __init__(
        self,
        left: UnaryExpression,
        right: UnaryExpression,
        operator: LivestatusOperator,
        header: str = "Filter",
    ):
        """Represent a binary operation.

        Note:
            This is used internally by the QueryExpression system, though you can construct the
            operation by hand. You need to pass in valid `UnaryExpression` instances for each
            argument of the operation.

        Args:
            left:
                The argument on the left side of the operation.

            right:
                The argument on the right side of the operation.

            operator:
                The operator which combines the two.

            header:
                The livestatus request header to use for this operation. This is 'Filter' by
                default, but can also be customized to support all the other filter-types (e.g.
                stats, etc.)

        """
        self.left = left
        self.right = right
        self.operator = operator
        self._header = header

    def __repr__(self):
        return "%s(%s %s %s)" % (
            self._header,
            self.left.value,
            self.operator,
            self.right.value,
        )

    def __str__(self):
        return "%s %s %s" % (self.left.value, self.operator, self.right.value)

    def render(self) -> RenderIntermediary:
        return [(self._header, str(self))]


class BoolExpression(QueryExpression):
    @property
    @abc.abstractmethod
    def expr(self):
        raise NotImplementedError()

    def __init__(self, *args: QueryExpression):
        self.args = args
        if not args:
            # For now this seems reasonable, but there are cases where it could be advantageous
            # to have empty arguments, though we'd have to decide on an actual use-case to be sure.
            raise ValueError("Need at least one parameter.")

    def __repr__(self):
        return f"{self.expr}{self.args!r}"

    def render(self) -> RenderIntermediary:
        # This is necessarily a bit ugly, due to some unavoidable edge-cases
        # in combination with NothingExpression().
        arg_count = len(self.args)
        result = []
        for arg in self.args:
            rendered = arg.render()
            if not rendered:
                # Nothing was rendered, so nothing to And() to, so we skip this argument.
                arg_count -= 1
                continue
            result.extend(rendered)

        # We only want to render our "And" or "Or" if we have more than one
        # argument. In case of only one argument it would be pointless.
        if arg_count > 1:
            # And: 1, Or: 4, etc...
            result.append((self.expr, "%d" % (arg_count,)))
        return result


class And(BoolExpression):
    """Constructs a logical And of multiple QueryExpression instances.

    >>> And(LiteralExpression("blah") == 1, LiteralExpression("hallo") == 0).render()
    [('Filter', 'blah = 1'), ('Filter', 'hallo = 0'), ('And', '2')]

    """

    expr = "And"


class Or(BoolExpression):
    """Constructs a logical Or of multiple QueryExpression instances.

    >>> Or(LiteralExpression("blah") == 1, LiteralExpression("hallo") == 0).render()
    [('Filter', 'blah = 1'), ('Filter', 'hallo = 0'), ('Or', '2')]

    """

    expr = "Or"


class Not(QueryExpression):
    """Negates a QueryExpression instance.

    >>> Not(Or(LiteralExpression("hurz") == 1)).render()
    [('Filter', 'hurz = 1'), ('Negate', '1')]

    """

    def __init__(self, other: QueryExpression):
        self.other = other

    def __repr__(self):
        return f"Not({self.other!r})"

    def render(self) -> RenderIntermediary:
        return self.other.render() + [("Negate", "1")]


def lookup_column(table_name, column_name) -> UnaryExpression:
    from cmk.utils.livestatus_helpers import tables

    if isinstance(table_name, str):
        table_class = getattr(tables, table_name.title())
    else:
        table_class = table_name
        table_name = table_class.__tablename__

    try:
        column = getattr(table_class, column_name)
    except AttributeError as e:
        raise ValueError(f"Table {table_name!r} has no column {column_name!r}.") from e
    return column.expr


def tree_to_expr(filter_dict, table: Any = None) -> QueryExpression:
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
                          {'op': '=', 'left': 'hosts.state', 'right': 0}]})
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

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
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
    if not isinstance(filter_dict, dict):
        # FIXME
        #   Because of not having correct Python packages at the root-level, sometimes a
        #   locally defined class ends up having a relative dotted path, like for example
        #       <class 'expressions.BinaryExpression'>
        #   instead of
        #       <class 'cmk.utils.livestatus_helpers.expressions.BinaryExpression'>
        #   While these classes are actually the same, Python treats them distinct, so we can't
        #   just say `isinstance(filter_dict, BinaryExpression)` (or their super-type) here.
        return cast(QueryExpression, filter_dict)
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
            lookup_column(_table, column),
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


def _table_name(table) -> str:
    if isinstance(table, str):
        return table

    return table.__tablename__

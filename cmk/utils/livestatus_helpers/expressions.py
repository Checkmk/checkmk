#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Livestatus Query Expression System

This will generate Livestatus queries from an abstract representation. This has the advantage
that each query is type-checked and can be easily parametrized without having to resort to
string concatenation.

It's implementation is still a bit rudimentary but supports most necessary concepts already.

"""

from __future__ import annotations

import abc
from typing import override

Primitives = str | int | bool | float | list[str] | tuple[str, ...]

# TODO: column functions
# TODO: more tests

RenderIntermediary = list[tuple[str, str]]

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

    @override
    def render(self) -> RenderIntermediary:
        return []


class UnaryExpression(abc.ABC):
    """Base class of all concrete single parts of BinaryExpression."""

    def __init__(self, value: str) -> None:
        # The value is used in the __repr__, if we don't set it before raising
        # the exception we get a new exception when the __repr__ is called,
        # e.g. by the crash reporting
        self.value = value
        if "\n" in value:
            raise ValueError("Illegal newline character in query")

    def op(self, operator: str, other: UnaryExpression | Primitives) -> BinaryExpression:
        other_expr: UnaryExpression
        if isinstance(other, list | tuple):
            other_expr = LiteralExpression(" ".join(other))
        elif isinstance(other, UnaryExpression):
            other_expr = other
        else:
            other_expr = LiteralExpression(str(other))
        return BinaryExpression(self, other_expr, operator)

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.value} 0x{id(self):x}>"

    @abc.abstractmethod
    @override
    def __eq__(self, other: Primitives) -> BinaryExpression:  # type: ignore[override]
        raise NotImplementedError()

    def __lt__(self, other: Primitives) -> BinaryExpression:
        return self.op("<", other)

    def __gt__(self, other: Primitives) -> BinaryExpression:
        return self.op(">", other)

    def __le__(self, other: Primitives) -> BinaryExpression:
        return self.op("<=", other)

    def __ge__(self, other: Primitives) -> BinaryExpression:
        return self.op(">=", other)

    @override
    def __ne__(self, other: Primitives) -> Not:  # type: ignore[override]
        return Not(self.__eq__(other))

    @abc.abstractmethod
    def equals(self, other: Primitives, ignore_case: bool = False) -> BinaryExpression:
        raise NotImplementedError()

    @abc.abstractmethod
    def contains(self, other: Primitives, ignore_case: bool = False) -> BinaryExpression:
        raise NotImplementedError()

    @abc.abstractmethod
    def disparity(self, other: Primitives, ignore_case: bool = False) -> BinaryExpression:
        raise NotImplementedError()

    @abc.abstractmethod
    def empty(self) -> BinaryExpression:
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

    @override
    def __eq__(self, other: Primitives) -> BinaryExpression:  # type: ignore[override]
        return self.op("=", other)

    @override
    def equals(self, other: Primitives, ignore_case: bool = False) -> BinaryExpression:
        if ignore_case:
            return self.op("=~", other)

        return self.op("=", other)

    @override
    def contains(self, other: Primitives, ignore_case: bool = False) -> BinaryExpression:
        if ignore_case:
            return self.op("~~", other)

        return self.op("~", other)

    @override
    def empty(self) -> BinaryExpression:
        raise NotImplementedError("Not implemented for this type.")

    @override
    def disparity(self, other: Primitives, ignore_case: bool = False) -> BinaryExpression:
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

    @override
    def __eq__(self, other: Primitives) -> BinaryExpression:  # type: ignore[override]
        return self.equals(other)

    @override
    def equals(self, other: Primitives, ignore_case: bool = False) -> BinaryExpression:
        if not other:
            # Check for empty list
            op = "="
        elif ignore_case:
            # case-insensitive equality
            op = "<="
        else:
            # equality
            op = ">="
        return self.op(op, other)

    @override
    def disparity(self, other: Primitives, ignore_case: bool = False) -> BinaryExpression:
        if ignore_case:
            op = ">"
        else:
            op = "<"
        return self.op(op, other)

    @override
    def contains(self, other: Primitives, ignore_case: bool = False) -> BinaryExpression:
        return self.op("~~", other)

    @override
    def empty(self) -> BinaryExpression:
        return self.op("=", LiteralExpression(""))


class LiteralExpression(ScalarExpression):
    """A literal value to be rendered in a Filter"""

    @override
    def disparity(self, other: Primitives, ignore_case: bool = False) -> BinaryExpression:
        raise NotImplementedError("Not implemented for this type.")

    @override
    def empty(self) -> BinaryExpression:
        raise NotImplementedError("Not implemented for this type.")


LivestatusOperator = str


class BinaryExpression(QueryExpression):
    """Represents a comparison of some sort.

    Examples:

        >>> fexp: BinaryExpression = LiteralExpression("hurz") == LiteralExpression("blah")
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

    @override
    def __repr__(self) -> str:
        return f"{self._header}({self.left.value} {self.operator} {self.right.value})"

    @override
    def __str__(self) -> str:
        return f"{self.left.value} {self.operator} {self.right.value}"

    @override
    def render(self) -> RenderIntermediary:
        return [(self._header, str(self))]


class BoolExpression(QueryExpression):
    expr: str

    def __init__(self, *args: QueryExpression) -> None:
        self.args = args
        if not args:
            # For now this seems reasonable, but there are cases where it could be advantageous
            # to have empty arguments, though we'd have to decide on an actual use-case to be sure.
            raise ValueError("Need at least one parameter.")

    @override
    def __repr__(self) -> str:
        return f"{self.expr}{self.args!r}"

    @override
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

    def __init__(self, other: QueryExpression) -> None:
        self.other = other

    @override
    def __repr__(self) -> str:
        return f"Not({self.other!r})"

    @override
    def render(self) -> RenderIntermediary:
        return self.other.render() + [("Negate", "1")]

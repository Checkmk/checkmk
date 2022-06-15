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
from typing import Any, List, Tuple

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

    def __repr__(self) -> str:
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

    def __repr__(self) -> str:
        return "%s(%s %s %s)" % (
            self._header,
            self.left.value,
            self.operator,
            self.right.value,
        )

    def __str__(self) -> str:
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

    def __repr__(self) -> str:
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

    def __repr__(self) -> str:
        return f"Not({self.other!r})"

    def render(self) -> RenderIntermediary:
        return self.other.render() + [("Negate", "1")]

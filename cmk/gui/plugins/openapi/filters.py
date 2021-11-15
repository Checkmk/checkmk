#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# binop
# logical op
# name
# value -> list[string], list[number], list[list[string]], etc, string, number

# ['=',['Host.name','heute']]
# Host.name=heute
import collections
import pprint
from typing import Tuple

import dateutil.parser
import pyparsing as pp  # type: ignore

from cmk.utils.livestatus_helpers import tables


class Node:
    def __init__(self, value):
        self.value = value
        self.parsed = self.parse(value)

    def parse(self, value):
        return value

    def __repr__(self):
        return f"{self.__class__.__name__}({self.parsed})"


class BinaryNode(Node):
    def parse(self, value):
        return tuple(value)


class DateTimeNode(Node):
    def parse(self, value):
        return dateutil.parser.isoparse(value[0])


class LogicalNode(Node):
    pass


class AndNode(LogicalNode):
    pass


class OrNode(LogicalNode):
    pass


class NotNode(LogicalNode):
    def parse(self, value):
        assert len(value) == 1
        return value[0]


class ColumnNode(Node):
    def parse(self, value):
        table_name, column_name = value
        table = getattr(tables, table_name.title())
        return getattr(table, column_name)


class InfixOpNode(Node):
    def parse(self, value):
        return value[0]


class IntNode(Node):
    def parse(self, value):
        return int(value[0])


class StringNode(Node):
    def parse(self, value):
        return value[0]


class RegexpNode(Node):
    def parse(self, value):
        return value[0]


class ListNode(Node):
    def parse(self, value):
        return value[0]


def make_grammar():
    name_expr = pp.Word(pp.alphas + "_").setName("Name")
    table_expr = pp.Word(pp.alphas + "_").setName("Table")
    column_expr = (
        (table_expr - pp.Suppress(".") - name_expr).setName("Column").setParseAction(ColumnNode)
    )

    number_expr = pp.Word(pp.nums).setName("number expression").setParseAction(IntNode)
    string_expr = pp.QuotedString(
        quoteChar='"', endQuoteChar='"', escChar="\\", unquoteResults=True
    ).setParseAction(StringNode)
    iso_date_time_expr = pp.pyparsing_common.iso8601_datetime.copy().setParseAction(DateTimeNode)

    list_expr = pp.Forward()
    value = string_expr | iso_date_time_expr | number_expr | list_expr
    list_expr <<= pp.nestedExpr(opener="[", closer="]", content=pp.delimitedList(value))
    list_expr.setName("list expression, starting with [ ending with ]")
    list_expr.setParseAction(ListNode)

    infix_op = pp.oneOf("< > = ~").setName("infix_op").setParseAction(InfixOpNode)

    regexp_expr = pp.QuotedString(
        quoteChar="/", endQuoteChar="/", escChar="\\", unquoteResults=True
    ).setParseAction(RegexpNode)

    binary_expression = (
        (column_expr - infix_op - (value | regexp_expr))
        .setName("binary expression")
        .setParseAction(BinaryNode)
    )

    logical_expression = pp.Forward()

    l_paren = pp.Suppress(pp.Literal("("))
    r_paren = pp.Suppress(pp.Literal(")"))

    trailing_comma = pp.Optional(pp.Suppress(pp.Literal(",")))

    base_expr = pp.Forward()

    def _logical_expr(name, expr_val, parse_action, single_argument=False):
        keyword = pp.Suppress(pp.CaselessKeyword(name))
        entries = expr_val.copy() if single_argument else pp.delimitedList(expr_val.copy())
        return keyword - l_paren - entries.setParseAction(parse_action) - trailing_comma - r_paren

    and_expression = _logical_expr("and", base_expr, AndNode)
    or_expression = _logical_expr("or", base_expr, OrNode)
    not_expression = _logical_expr("not", base_expr, NotNode, single_argument=True)

    log_expression = and_expression | or_expression | not_expression
    logical_expression <<= log_expression.setName("logical expression")
    base_expr <<= logical_expression | binary_expression

    return base_expr


def parse_filter(fstr: str):
    """
    >>> parse_filter(r'''
    ... and(
    ...     or(
    ...         or(
    ...             not(
    ...                 and(
    ...                     hosts.name = 2,
    ...                     hosts.alias = "fo\\"obar",
    ...                     hosts.alias ~ [1, [2, "fo"], 3],
    ...                 )
    ...             ),
    ...             hosts.name ~ /^foo bar$/,
    ...             hosts.name = 2010-01-01T10:10:10Z,
    ...         )
    ...     )
    ... )
    ... ''')
    AndNode([OrNode([OrNode([NotNode(AndNode([BinaryNode((ColumnNode(name),\
 InfixOpNode(=), IntNode(2))), BinaryNode((ColumnNode(alias),\
 InfixOpNode(=), StringNode(fo"obar))), BinaryNode((ColumnNode(alias),\
 InfixOpNode(~), ListNode([IntNode(1), ListNode([IntNode(2), StringNode(fo)]), IntNode(3)])))])),\
 BinaryNode((ColumnNode(name), InfixOpNode(~), RegexpNode(^foo bar$))),\
 BinaryNode((ColumnNode(name), InfixOpNode(=),\
 DateTimeNode(2010-01-01 10:10:10+00:00)))])])])

    """
    grammar = make_grammar()
    try:
        parsed = grammar.parseString(fstr).asList()
    except pp.ParseSyntaxException as exc:
        raise Exception(exc.msg, exc.markInputline())
    assert len(parsed) == 1
    root_expr = parsed[0]
    return pprint.pprint(root_expr)


def nested_loop_join(t1, t2, key1: Tuple[str, ...], key2: Tuple[str, ...]):
    """Joins two datasets with the nested-loop join algorithm.

    >>> l1 = [{'a': 1}, {'a': 2}]
    >>> l2 = [{'a': 1, 'b': 2, 'c': 3}, {'a': 2, 'b': 1, 'c': 3}]
    >>> list(nested_loop_join(l1, l2, ('a',), ('b',)))
    [({'a': 1}, {'a': 2, 'b': 1, 'c': 3}), ({'a': 2}, {'a': 1, 'b': 2, 'c': 3})]

    >>> list(nested_loop_join(l1, l2, ('a', 'a'), ('b', 'c')))
    []

    Args:
        t1:
        t2:
        key1:
        key2:

    Returns:

    """
    for e1 in t1:
        for e2 in t2:
            if all(e1[k1] == e2[k2] for k1, k2 in zip(key1, key2)):
                yield e1, e2


# Query([Hosts.name, Services.description, Services.state_type, Services.staleness])
# action(live, hosts_name, services_description):

# Hosts.name <- Services.host_name
# Hosts.name <- Logs.host_name
# Hosts.name <- Downtimes.host_name


def hash_join(
    t1,
    t2,
    key1: Tuple[str, ...],
    key2: Tuple[str, ...],
):
    """Joins two datasets with the hash-join algorithm.

    Notes:
        This function only implements simple comparison joins. No effort is made for more complex
        join conditions, or IN / NOT IN conditions.

    Examples:

        >>> l1 = [{'a': 1}, {'a': 2}]
        >>> l2 = [{'a': 1, 'b': 2, 'c': 3}, {'a': 2, 'b': 1, 'c': 3}]
        >>> list(hash_join(l1, l2, ('a',), ('b',)))
        [({'a': 1}, {'a': 2, 'b': 1, 'c': 3}), ({'a': 2}, {'a': 1, 'b': 2, 'c': 3})]

        >>> list(hash_join(l1, l2, ('a', 'a'), ('b', 'c')))
        []

    Args:
        t1:
            The first table. A sequence of dictionaries is assumed.
        t2:
            The second table. A sequence of dictionaries is assumed.
        key1:
            The key(s) of the first table.
        key2:
            The key(s) of the second table.

    Returns:
        A generator which emits entry tuples of both tables, where the key is identical. Entries of
        the table may occur more than once. Entries of the first table are guaranteed to not be
        duplicated.

    """
    # This works either way. From t1 to t2 or the other way around. The only difference is the
    # efficiency, which we can't predict because it's dependent on the tables that are passed in.

    # Build phase
    # We store the positions of the concrete keys in a dictionary. As keys may occur more than once
    # the dictionary stores a list of locations for each key.
    i2 = collections.defaultdict(list)
    for count2, e2 in enumerate(t2):
        key = tuple(e2[k2] for k2 in key2)
        i2[key].append(count2)

    # Probe phase
    # Go over the stored positions and emit the rows with matching keys. This operates over
    # potentially way less data than the less efficient nested_loop_join algorithm (which is N*M).
    for e1 in t1:
        key = tuple(e1[k1] for k1 in key1)
        if key in i2:
            # The key may occur at multiple positions if it is not the primary key.
            for pos in i2[key]:
                yield e1, t2[pos]

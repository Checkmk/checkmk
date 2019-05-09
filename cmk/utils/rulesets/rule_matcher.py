#!/usr/bin/env python2
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""This module provides generic Check_MK rule matching functionality

A ruleset contains a collection of rules which each has a condition
specification. These conditions are based on the MongoDB query syntax , but do
only implement a subset of features that we need for our logic.

# See:
# https://docs.mongodb.com/manual/tutorial/query-documents/
# https://docs.mongodb.com/manual/reference/operator/query/
# https://github.com/mongodb-js/mongodb-language-model/blob/master/docs/bnf.md

Implemented:

- Comparison Query Operators
  - all
- Logical Query Operators
  - all
- Evaluation Query Operators:
  - only $regex (only /pattern/<options> form)

In case we need more one day use the features that the MongoDB query syntax
offers.
"""

import re
import collections
import operator
import six

import cmk.utils.log
from cmk.utils.exceptions import MKException

# TODO: Implement rule diagnose: match / not matching reason (needed in GUI)

logger = cmk.utils.log.get_logger(__name__)


class MatchingError(MKException):
    """Is raised whenever an issue occurs while matching rule conditions"""
    pass


class RuleMatcher(object):
    def match(self, document, expression):
        """Whether or not the given filter expression matches the given object
        In case of an error during processing a MatchingError() is raised
        """
        if not isinstance(expression, collections.Mapping):
            raise MatchingError("Need mapping object as expression")

        if not isinstance(document, collections.Mapping):
            raise MatchingError("Need mapping object as document")

        try:
            return all(self._match(document, expression))
        except MatchingError:
            raise
        except Exception as e:
            raise MatchingError("Matching error: %s" % e)

    def _match(self, document, expression):
        # We either directly have a single leaf clause or an expression tree clause
        for field_or_op, cond in expression.iteritems():
            if isinstance(field_or_op, six.string_types) and field_or_op.startswith("$"):
                try:
                    yield _tree_operators[field_or_op](document, cond, self._match)
                    continue
                except KeyError:
                    raise MatchingError("Unknown tree operator: %s" % field_or_op)

            yield self._match_leaf_clause(document, field_or_op, cond)

    def _match_leaf_clause(self, document, field, condition):
        field_exists, value = True, None
        try:
            value = self._get_value(document, field)
        except KeyError:
            field_exists = False

        if isinstance(condition, collections.Mapping):
            # There are two options for dicts. It's either a operator object or
            # a nested document match (which is only possible as full document
            # equal comparison). In case of an operator object all keys are operators.
            if self._is_operator_object(condition):
                return all(self._match_operator_object(value, condition))

        # Realize the leaf equal comparison
        return field_exists and value == condition

    def _get_value(self, document, field):
        """Returns either the value or raises a KeyError in case the field does not exist
        This method implements the ability to query fields of nested documents.
        """
        if not isinstance(field, six.string_types) or "." not in field:
            return document[field]

        return reduce(operator.getitem, field.split("."), document)

    def _is_operator_object(self, condition):
        """Once one operator field is found in the expression"""
        return any(c[0] == "$" for c in condition)

    def _match_operator_object(self, value, condition):
        for op, cond in condition.iteritems():
            if op == "$not":
                yield not all(self._match_operator_object(value, cond))
                continue

            # The $options operator is not an operator on its own, but an
            # addition to the $regex operator. Likewise the $regex operator
            # can not directly work with the cond. Instead it needs the whole
            # condition expression to have access to "$regex" and "$options"
            #
            # Strange that this is not handled in a sub-expression, something
            # like this: {$regex: {$pattern: "...", $options: "..."}}
            #
            # No. It's like this: {$regex: "pattern", $options}
            #
            # We also adapt the validation here form the mongodb.
            if op == "$options":
                if "$regex" not in condition:
                    raise MatchingError("$options needs a $regex")
                continue

            if op == "$regex":
                yield _regex(value, condition)
                continue

            try:
                yield _comparison_operators[op](value, cond)
            except KeyError:
                raise MatchingError("Unknown value operator: %s" % op)


def _and(entry, condition, match_func):
    if not isinstance(condition, list):
        raise MatchingError("Invalid argument for $and: %r" % condition)
    return all(all(match_func(entry, c)) for c in condition)


def _or(entry, condition, match_func):
    if not isinstance(condition, list):
        raise MatchingError("Invalid argument for $or: %r" % condition)
    return any(all(match_func(entry, c)) for c in condition)


def _nor(entry, condition, match_func):
    if not isinstance(condition, list):
        raise MatchingError("Invalid argument for $nor: %r" % condition)
    return all(not all(match_func(entry, c)) for c in condition)


def _regex(entry, condition):
    if entry is None:
        return False

    supported_flags = [("i", re.I), ("m", re.M), ("s", re.S), ("x", re.X)]
    flags = reduce(operator.or_,
                   (v for c, v in supported_flags if c in condition.get("$options", [])), 0)

    try:
        return bool(re.search(condition["$regex"], entry, flags=flags))
    except Exception as e:
        raise MatchingError("Invalid regex: %s" % e)


_comparison_operators = {
    "$in": lambda a, b: operator.contains(b, a),
    "$nin": lambda a, b: not operator.contains(b, a),
    "$eq": operator.eq,
    "$ne": operator.ne,
    "$gt": operator.gt,
    "$gte": operator.ge,
    "$lt": operator.lt,
    "$lte": operator.le,
}

_tree_operators = {
    "$and": _and,
    "$nor": _nor,
    "$or": _or,
}

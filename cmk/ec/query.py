#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
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

from logging import Logger  # pylint: disable=unused-import
from typing import Any, Callable, List, Optional, Set, Tuple  # pylint: disable=unused-import

from cmk.utils.exceptions import MKException
import cmk.utils.regex


class MKClientError(MKException):
    pass


# TODO: Extract StatusServer and friends...
_StatusServer = Any


class Query:
    @staticmethod
    def make(status_server, raw_query, logger):
        # type: (_StatusServer, List[str], Logger) -> Query
        parts = raw_query[0].split(None, 1)
        if len(parts) != 2:
            raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")
        method = parts[0]
        if method == "GET":
            return QueryGET(status_server, raw_query, logger)
        if method == "REPLICATE":
            return _QueryREPLICATE(status_server, raw_query, logger)
        if method == "COMMAND":
            return _QueryCOMMAND(status_server, raw_query, logger)
        raise MKClientError("Invalid method %s (allowed are GET, REPLICATE, COMMAND)" % method)

    def __init__(self, status_server, raw_query, logger):
        # type: (_StatusServer, List[str], Logger) -> None
        super().__init__()
        self.output_format = "python"
        parts = raw_query[0].split(None, 1)
        if len(parts) != 2:
            raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")
        self.method, self.method_arg = parts

    def __repr__(self):
        # type: () -> str
        return self.method + " " + self.method_arg


_filter_operators = {
    "=": (lambda a, b: a == b),
    ">": (lambda a, b: a > b),
    "<": (lambda a, b: a < b),
    ">=": (lambda a, b: a >= b),
    "<=": (lambda a, b: a <= b),
    "~": (lambda a, b: cmk.utils.regex.regex(b).search(a)),
    "=~": (lambda a, b: a.lower() == b.lower()),
    "~~": (lambda a, b: cmk.utils.regex.regex(b.lower()).search(a.lower())),
    "in": (lambda a, b: a in b),
}


def operator_for(name):
    # type: (str) -> Callable
    func = _filter_operators.get(name)
    if func is None:
        raise MKClientError("Unknown filter operator '%s'" % name)
    return func


class QueryGET(Query):
    def __init__(self, status_server, raw_query, logger):
        # type: (_StatusServer, List[str], Logger) -> None
        super().__init__(status_server, raw_query, logger)
        self.table_name = self.method_arg
        self.table = status_server.table(self.table_name)
        self.requested_columns = self.table.column_names
        # NOTE: history's _get_mongodb and _get_files access filters and limits directly.
        self.filters = []  # type: List[Tuple[str, str, Callable, str]]
        self.limit = None  # type: Optional[int]
        # NOTE: StatusTableEvents uses only_host for optimization.
        self.only_host = None  # type: Optional[Set[Any]]
        self._parse_header_lines(raw_query, logger)

    def _parse_header_lines(self, raw_query, logger):
        # type: (List[str], Logger) -> None
        for line in raw_query[1:]:
            try:
                header, argument = line.rstrip("\n").split(":", 1)
                self._parse_header_line(header, argument.lstrip(" "), logger)
            except Exception as e:
                raise MKClientError("Invalid header line '%s': %s" % (line.rstrip(), e))

    def _parse_header_line(self, header, argument, logger):
        # type: (str, str, Logger) -> None
        if header == "OutputFormat":
            if argument not in ["python", "plain", "json"]:
                raise MKClientError(
                    "Invalid output format \"%s\" (allowed are: python, plain, json)" % argument)
            self.output_format = argument
        elif header == "Columns":
            self.requested_columns = argument.split(" ")
        elif header == "Filter":
            column_name, operator_name, predicate, argument = self._parse_filter(argument)
            # Needed for later optimization (check_mkevents)
            if column_name == "event_host" and operator_name == 'in':
                self.only_host = set(argument)
            self.filters.append((column_name, operator_name, predicate, argument))
        elif header == "Limit":
            self.limit = int(argument)
        else:
            logger.info("Ignoring not-implemented header %s" % header)

    def _parse_filter(self, textspec):
        # type: (str) -> Tuple[str, str, Callable, Any]
        # Examples:
        # id = 17
        # name ~= This is some .* text
        # host_name =
        parts = textspec.split(None, 2)
        if len(parts) == 2:
            parts.append("")
        column, operator_name, raw_argument = parts

        try:
            convert = self.table.column_types[column]
        except KeyError:
            raise MKClientError("Unknown column: %s (Available are: %s)" %
                                (column, self.table.column_names))

        # TODO: BUG: The query is decoded to unicode after receiving it from
        # the socket. The columns with type str (initialied with "") will apply
        # str(argument) here and convert the value back to str! This will crash
        # when the filter contains non ascii characters!
        # Fix this by making the default values unicode and skip unicode conversion
        # here (for performance reasons) because argument is already unicode.
        # TODO: Fix the typing chaos below!
        argument = [convert(arg) for arg in raw_argument.split()
                   ] if operator_name == 'in' else convert(raw_argument)

        operator_function = operator_for(operator_name)
        return (column, operator_name, lambda x: operator_function(x, argument), argument)

    def requested_column_indexes(self):
        # type: () -> List[Optional[int]]
        # If a column is not known: Use None as index and None value later.
        return [
            self.table.column_indices.get(column_name)  #
            for column_name in self.requested_columns
        ]

    def filter_row(self, row):
        # type: (List[Any]) -> bool
        return all(
            predicate(row[self.table.column_indices[column_name]])
            for column_name, _operator_name, predicate, _argument in self.filters)


class _QueryREPLICATE(Query):
    pass


class _QueryCOMMAND(Query):
    pass

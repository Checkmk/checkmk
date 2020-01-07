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

from cmk.utils.exceptions import MKException
import cmk.utils.regex


class MKClientError(MKException):
    pass


class Query:
    @staticmethod
    def make(status_server, raw_query, logger):
        parts = raw_query[0].split(None, 1)
        if len(parts) != 2:
            raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")
        method = parts[0]
        if method == "GET":
            return _QueryGET(status_server, raw_query, logger)
        if method == "REPLICATE":
            return _QueryREPLICATE(status_server, raw_query, logger)
        if method == "COMMAND":
            return _QueryCOMMAND(status_server, raw_query, logger)
        raise MKClientError("Invalid method %s (allowed are GET, REPLICATE, COMMAND)" % method)

    def __init__(self, status_server, raw_query, logger):
        super().__init__()

        self._logger = logger
        self.output_format = "python"

        self._raw_query = raw_query
        self._from_raw_query(status_server)

    def _from_raw_query(self, status_server):
        self._parse_method_and_args()

    def _parse_method_and_args(self):
        parts = self._raw_query[0].split(None, 1)
        if len(parts) != 2:
            raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")

        self.method, self.method_arg = parts

    def __repr__(self):
        return repr("\n".join(self._raw_query))


class _QueryGET(Query):
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

    def _from_raw_query(self, status_server):
        super()._from_raw_query(status_server)
        self._parse_table(status_server)
        self._parse_header_lines()

    def _parse_table(self, status_server):
        self.table_name = self.method_arg
        self.table = status_server.table(self.table_name)

    def _parse_header_lines(self):
        self.requested_columns = self.table.column_names  # use all columns as default
        self.filters = []
        self.limit = None
        self.only_host = None

        self.header_lines = []
        for line in self._raw_query[1:]:
            try:
                header, argument = line.rstrip("\n").split(":", 1)
                argument = argument.lstrip(" ")

                if header == "OutputFormat":
                    if argument not in ["python", "plain", "json"]:
                        raise MKClientError(
                            "Invalid output format \"%s\" (allowed are: python, plain, json)" %
                            argument)

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
                    self._logger.info("Ignoring not-implemented header %s" % header)

            except Exception as e:
                raise MKClientError("Invalid header line '%s': %s" % (line.rstrip(), e))

    def _parse_filter(self, textspec):
        # Examples:
        # id = 17
        # name ~= This is some .* text
        # host_name =
        parts = textspec.split(None, 2)
        if len(parts) == 2:
            parts.append("")
        column, operator_name, argument = parts

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
        if operator_name == 'in':
            argument = list(map(convert, argument.split()))
        else:
            argument = convert(argument)

        operator_function = self._filter_operators.get(operator_name)
        if not operator_function:
            raise MKClientError("Unknown filter operator '%s'" % operator_name)

        return (column, operator_name, lambda x: operator_function(x, argument), argument)

    def requested_column_indexes(self):
        indexes = []

        for column_name in self.requested_columns:
            try:
                column_index = self.table.column_indices[column_name]
            except KeyError:
                # The column is not known: Use None as index and None value later
                column_index = None
            indexes.append(column_index)

        return indexes

    def filter_row(self, row):
        for column_name, _operator_name, predicate, _argument in self.filters:
            if not predicate(row[self.table.column_indices[column_name]]):
                return None
        return row


class _QueryREPLICATE(Query):
    pass


class _QueryCOMMAND(Query):
    pass

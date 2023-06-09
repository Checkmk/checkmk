#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import operator
from collections.abc import Callable, Sequence
from logging import Logger
from typing import Any, Literal

import cmk.utils.regex
from cmk.utils.exceptions import MKException


class MKClientError(MKException):
    pass


# TODO: Extract StatusServer and friends...
_StatusServer = Any


class Query:
    @staticmethod
    def make(status_server: _StatusServer, raw_query: list[str], logger: Logger) -> "Query":
        parts = raw_query[0].split(None, 1)
        if len(parts) != 2:
            raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")
        method = parts[0]
        if method == "GET":
            return QueryGET(status_server, raw_query, logger)
        if method == "REPLICATE":
            return QueryREPLICATE(status_server, raw_query, logger)
        if method == "COMMAND":
            return QueryCOMMAND(status_server, raw_query, logger)
        raise MKClientError(f"Invalid method {method} (allowed are GET, REPLICATE, COMMAND)")

    def __init__(self, status_server: _StatusServer, raw_query: list[str], logger: Logger) -> None:
        self.output_format = "python"
        parts = raw_query[0].split(None, 1)
        if len(parts) != 2:
            raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")
        self.__method, self.method_arg = parts

    def __repr__(self) -> str:
        return self.__method + " " + self.method_arg


def filter_operator_in(a: Any, b: Any) -> bool:
    """Implemented as a named function, as it is used in a second filter
    cmk.ec.main: StatusTableEvents._enumerate
    not implemented as regex/IGNORECASE due to performance"""
    return a.lower() in (e.lower() for e in b)


OperatorName = Literal["=", ">", "<", ">=", "<=", "~", "=~", "~~", "in"]


# NOTE: mypy is currently too dumb to narrow down a type via "in" or "get()", so we have to work
# around that somehow: We either duplicate the operator names below or we introduce a case in
# operator_for(). We're choosing evil no. 1... :-/
_filter_operators: dict[str, tuple[OperatorName, Callable[[Any, Any], bool]]] = {
    "=": ("=", operator.eq),
    ">": (">", operator.gt),
    "<": ("<", operator.lt),
    ">=": (">=", operator.ge),
    "<=": ("<=", operator.le),
    "~": ("~", lambda a, b: bool(cmk.utils.regex.regex(b).search(a))),
    "=~": ("=~", lambda a, b: a.lower() == b.lower()),
    "~~": ("~~", lambda a, b: bool(cmk.utils.regex.regex(b.lower()).search(a.lower()))),
    "in": ("in", filter_operator_in),
}


def operator_for(name: str) -> tuple[OperatorName, Callable[[Any, Any], bool]]:
    name_and_func = _filter_operators.get(name)
    if name_and_func is None:
        raise MKClientError(f"Unknown filter operator '{name}'")
    return name_and_func


class QueryGET(Query):
    def __init__(self, status_server: _StatusServer, raw_query: list[str], logger: Logger) -> None:
        super().__init__(status_server, raw_query, logger)
        self.table_name = self.method_arg
        self.table = status_server.table(self.table_name)
        self.requested_columns = self.table.column_names
        # NOTE: history's _get_mongodb and _get_files access filters and limits directly.
        self.filters: list[tuple[str, OperatorName, Callable[[Any], bool], Any]] = []
        self.limit: int | None = None
        # NOTE: StatusTableEvents uses only_host for optimization.
        self.only_host: set[Any] | None = None
        self._parse_header_lines(raw_query, logger)

    def _parse_header_lines(self, raw_query: list[str], logger: Logger) -> None:
        for line in raw_query[1:]:
            try:
                header, argument = line.rstrip("\n").split(":", 1)
                self._parse_header_line(header, argument.lstrip(" "), logger)
            except Exception as e:
                raise MKClientError(f"Invalid header line '{line.rstrip()}'") from e

    def _parse_header_line(self, header: str, argument: str, logger: Logger) -> None:
        if header == "OutputFormat":
            if argument not in ["python", "plain", "json"]:
                raise MKClientError(
                    f'Invalid output format "{argument}" (allowed are: python, plain, json)'
                )
            self.output_format = argument
        elif header == "Columns":
            self.requested_columns = argument.split(" ")
        elif header == "Filter":
            column_name, operator_name, predicate, argument = self._parse_filter(argument)
            # Needed for later optimization (check_mkevents)
            if column_name == "event_host" and operator_name == "in":
                self.only_host = set(argument)
            self.filters.append((column_name, operator_name, predicate, argument))
        elif header == "Limit":
            self.limit = int(argument)
        else:
            logger.info("Ignoring not-implemented header %s", header)

    def _parse_filter(self, textspec: str) -> tuple[str, OperatorName, Callable[[Any], bool], Any]:
        """Examples:
        id = 17
        name ~= This is some .* text
        host_name ="""
        parts = textspec.split(None, 2)
        if len(parts) == 2:
            parts.append("")
        column, operator_name, raw_argument = parts

        try:
            convert = self.table.column_types[column]
        except KeyError as e:
            raise MKClientError(
                f"Unknown column: {column} (Available are: {self.table.column_names})"
            ) from e

        op_name, operator_function = operator_for(operator_name)
        # TODO: BUG: The query is decoded to unicode after receiving it from
        # the socket. The columns with type str (initialized with "") will apply
        # str(argument) here and convert the value back to str! This will crash
        # when the filter contains non ascii characters!
        # Fix this by making the default values unicode and skip unicode conversion
        # here (for performance reasons) because argument is already unicode.
        # TODO: Fix the typing chaos below!
        argument = (
            [convert(arg) for arg in raw_argument.split()]
            if op_name == "in"
            else convert(raw_argument)
        )

        return (column, op_name, lambda x: operator_function(x, argument), argument)

    def requested_column_indexes(self) -> list[int | None]:
        """If a column is not known: Use None as index and None value later."""
        return [
            self.table.column_indices.get(column_name) for column_name in self.requested_columns
        ]

    def filter_row(self, row: Sequence[Any]) -> bool:
        return all(
            predicate(row[self.table.column_indices[column_name]])
            for column_name, _operator_name, predicate, _argument in self.filters
        )


class QueryREPLICATE(Query):
    pass


class QueryCOMMAND(Query):
    pass

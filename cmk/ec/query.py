#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import operator
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from logging import Logger
from typing import Any, Literal

from cmk.ccc.exceptions import MKException

import cmk.utils.regex


class MKClientError(MKException):
    pass


Columns = Sequence[tuple[str, float | int | str | Sequence[object]]]

#  Common functionality for the event/history/rule/status tables
#
# If you need a new column here, then these are the places to change:
# bin/mkeventd:
# - add column to the end of StatusTableEvents.columns
# - add column to grepping_filters if it is a str column
# - deal with convert_history_line() (if not a str column)
# - make sure that the new column is filled at *every* place where
#   an event is being created:
#   * _create_event_from_trap()
#   * create_event_from_syslog_message()
#   * _handle_absent_event()
#   * _create_overflow_event()
# - When loading the status file add the possibly missing column to all
#   loaded events (load_status())
# - Maybe add matching/rewriting for the new column
# - write the actual code using the new column
# web:
# - Add column painter for the new column
# - Create a sorter
# - Create a filter
# - Add painter and filter to all views where appropriate
# - maybe add WATO code for matching rewriting
# - do not forget event_rule_matches() in web!
# - maybe add a field into the event simulator


class StatusTable:
    """Common functionality for the event/history/rule/status tables."""

    name: str
    prefix: str | None = None
    columns: Columns = []

    @abc.abstractmethod
    def _enumerate(self, query: QueryGET) -> Iterable[Sequence[object]]:
        """
        Must return a enumerable type containing fully populated lists (rows) matching the
        columns of the table.
        """
        raise NotImplementedError

    def __init__(self, logger: Logger) -> None:
        self._logger = logger.getChild(f"status_table.{self.prefix}")
        self.column_names = [name for name, _def_val in self.columns]
        self.column_types = {name: type(def_val) for name, def_val in self.columns}
        self.column_indices = {name: index for index, name in enumerate(self.column_names)}

    def query(self, query: QueryGET) -> Iterable[Sequence[object]]:
        requested_column_indexes = query.requested_column_indexes()

        # Output the column headers
        # TODO: Add support for ColumnHeaders like in livestatus?
        yield query.requested_columns

        num_rows = 0
        for row in self._enumerate(query):
            if query.limit is not None and num_rows >= query.limit:
                break  # The maximum number of rows has been reached
            # Apply filters
            # TODO: History filtering is done in history load code. Check for improvements
            if query.table.name == "history" or query.filter_row(row):
                yield self._build_result_row(row, requested_column_indexes)
                num_rows += 1

    def _build_result_row(
        self, row: Sequence[object], requested_column_indexes: list[int | None]
    ) -> list[object]:
        return [(None if index is None else row[index]) for index in requested_column_indexes]


class Query:
    @staticmethod
    def make(
        get_table: Callable[[str], StatusTable], raw_query: list[str], logger: Logger
    ) -> Query:
        parts = raw_query[0].split(None, 1)
        if len(parts) != 2:
            raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")
        method = parts[0]
        if method == "GET":
            return QueryGET(get_table, raw_query, logger)
        if method == "REPLICATE":
            return QueryREPLICATE(raw_query, logger)
        if method == "COMMAND":
            return QueryCOMMAND(raw_query, logger)
        raise MKClientError(f"Invalid method {method} (allowed are GET, REPLICATE, COMMAND)")

    def __init__(self, raw_query: list[str], logger: Logger) -> None:
        self.output_format = "python"
        parts = raw_query[0].split(None, 1)
        if len(parts) != 2:
            raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")
        self.__method, self.method_arg = parts

    def __repr__(self) -> str:
        return self.__method + " " + self.method_arg


def filter_operator_in(a: str, b: Iterable[str]) -> bool:
    """Implemented as a named function, as it is used in a second filter
    cmk.ec.main: StatusTableEvents._enumerate
    not implemented as regex/IGNORECASE due to performance.
    """
    return a.lower() in {e.lower() for e in b}


OperatorName = Literal["=", ">", "<", ">=", "<=", "~", "=~", "~~", "in"]


@dataclass(frozen=True)
class QueryFilter:
    column_name: str
    operator_name: OperatorName
    predicate: Callable[[object], bool]
    argument: Any


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
    def __init__(
        self, get_table: Callable[[str], StatusTable], raw_query: list[str], logger: Logger
    ) -> None:
        super().__init__(raw_query, logger)
        self.table = get_table(self.method_arg)
        self.requested_columns = self.table.column_names
        # NOTE: history's _get_mongodb and _get_files access filters and limits directly.
        self.filters: list[QueryFilter] = []
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
            if argument not in {"python", "plain", "json"}:
                raise MKClientError(
                    f'Invalid output format "{argument}" (allowed are: python, plain, json)'
                )
            self.output_format = argument
        elif header == "Columns":
            self.requested_columns = argument.split(" ")
        elif header == "Filter":
            f = self._parse_filter(argument)
            # Needed for later optimization (check_mkevents)
            if f.column_name == "event_host" and f.operator_name == "in":
                self.only_host = set(f.argument)
            self.filters.append(f)
        elif header == "Limit":
            self.limit = int(argument)
        else:
            logger.info("Ignoring not-implemented header %s", header)

    def _parse_filter(self, textspec: str) -> QueryFilter:
        """Examples:
        id = 17
        name ~= This is some .* text
        host_name =
        """
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
            [convert(arg) for arg in raw_argument.split()]  # type: ignore[call-arg]
            if op_name == "in"
            else convert(raw_argument)  # type: ignore[call-arg]
        )

        return QueryFilter(
            column_name=column,
            operator_name=op_name,
            predicate=lambda x: operator_function(x, argument),
            argument=argument,
        )

    def requested_column_indexes(self) -> list[int | None]:
        """If a column is not known: Use None as index and None value later."""
        return [
            self.table.column_indices.get(column_name) for column_name in self.requested_columns
        ]

    def filter_row(self, row: Sequence[object]) -> bool:
        return all(f.predicate(row[self.table.column_indices[f.column_name]]) for f in self.filters)


class QueryREPLICATE(Query):
    pass


class QueryCOMMAND(Query):
    pass

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"


import abc
import operator
import re
import string
from collections.abc import Callable, Iterable, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from logging import Logger
from typing import Any, ClassVar, Literal, override

from cmk.ccc.exceptions import MKException


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

    name: ClassVar[str]
    prefix: ClassVar[str]
    columns: ClassVar[Columns]
    # Whether _enumerate() returns only the rows which the filters of the query select
    filters_itself: ClassVar[bool] = False

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
            if self.filters_itself or query.filter_row(row):
                yield self._build_result_row(row, requested_column_indexes)
                num_rows += 1

    def _build_result_row(
        self, row: Sequence[object], requested_column_indexes: list[int | None]
    ) -> list[object]:
        return [(None if index is None else row[index]) for index in requested_column_indexes]


# The whitespace of Livestatus, i.e. of C's isspace() in the C locale
_ASCII_WHITESPACE = string.whitespace


def _ascii_split(text: str) -> list[str]:
    """Like str.split() without a separator, but only at the whitespace of Livestatus"""
    stripped = text.strip(_ASCII_WHITESPACE)
    return re.split(r"\s+", stripped, flags=re.ASCII) if stripped else []


def request_lines(request: bytes) -> list[str]:
    """Splits a request of a client into its lines

    Only "\\n" ends a line, while str.splitlines() splits at other line boundaries like
    U+2028, too. With those, a value in a header line, e.g. the regex of a filter, could
    inject further header lines. Like Livestatus, we drop ASCII whitespace at the end of
    each line, which includes the "\\r" of CRLF line endings, and lines with only
    whitespace. Note that Queries ends a request at "\\n\\n" only, not at "\\r\\n\\r\\n", so a
    client using CRLF line endings has to end the request with "\\n\\n" or by closing its
    side of the connection."""
    raw_lines = request.decode("utf-8").removesuffix("\n").split("\n")
    if raw_lines[0] == "":
        # An empty line ends a request, so like in Livestatus, this request is empty.
        return []
    lines = (line.rstrip(_ASCII_WHITESPACE) for line in raw_lines)
    return [line for line in lines if line]


def _method_and_argument(raw_query: list[str]) -> tuple[str, str]:
    """Splits the first line of a query like Livestatus: A space ends the method, and
    the argument starts after any further ASCII whitespace."""
    method, space, argument = (raw_query[0] if raw_query else "").partition(" ")
    argument = argument.lstrip(_ASCII_WHITESPACE)
    if not space or not argument:
        raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")
    return method, argument


class Query:
    @staticmethod
    def make(
        get_table: Callable[[str], StatusTable], raw_query: list[str], logger: Logger
    ) -> Query:
        method, _argument = _method_and_argument(raw_query)
        if method == "GET":
            return QueryGET(get_table, raw_query, logger)
        if method == "REPLICATE":
            return QueryREPLICATE(raw_query, logger)
        if method == "COMMAND":
            return QueryCOMMAND(raw_query, logger)
        raise MKClientError(f"Invalid method {method} (allowed are GET, REPLICATE, COMMAND)")

    def __init__(self, raw_query: list[str], logger: Logger) -> None:  # noqa: ARG002
        self.output_format = "python"
        self.__method, self.method_arg = _method_and_argument(raw_query)

    @override
    def __repr__(self) -> str:
        return self.__method + " " + self.method_arg


# The operators compare the value of a row with the argument of a filter, which they prepare
# only once for all rows, e.g. by compiling a regex, see _filter_operators.


def _unchanged(argument: Any) -> Any:
    return argument


def _lowered_set(arguments: Iterable[str]) -> AbstractSet[str]:
    return {argument.lower() for argument in arguments}


def _regex(argument: str) -> re.Pattern[str]:
    return re.compile(argument)


def _regex_ignoring_case(argument: str) -> re.Pattern[str]:
    return re.compile(argument, re.IGNORECASE)


def filter_operator_in(a: str, b: AbstractSet[str]) -> bool:
    """Whether a is in b ignoring case, where b is lowered, see _lowered_set(). A regex with
    IGNORECASE would be slower."""
    return a.lower() in b


# None stands for a missing value, which neither matches nor equals anything, so
# the negated operators select it, just like operator.ne does.
def _matches(value: str | None, regex: re.Pattern[str]) -> bool:
    return value is not None and regex.search(value) is not None


def _equals_ignoring_case(value: str | None, lowered: str) -> bool:
    return value is not None and value.lower() == lowered


OperatorName = Literal["=", "!=", "~", "!~", "=~", "!=~", "~~", "!~~", "<", ">=", ">", "<=", "in"]


@dataclass(frozen=True)
class QueryFilter:
    column_name: str
    operator_name: OperatorName
    predicate: Callable[[object], bool]
    argument: Any


# NOTE: mypy is currently too dumb to narrow down a type via "in" or "get()", so we have to work
# around that somehow: We either duplicate the operator names below or we introduce a case in
# _operator(). We're choosing evil no. 1... :-/
_Operator = tuple[OperatorName, Callable[[Any], Any], Callable[[Any, Any], bool]]
_filter_operators: dict[str, _Operator] = {
    "=": ("=", _unchanged, operator.eq),
    "!=": ("!=", _unchanged, operator.ne),
    "~": ("~", _regex, _matches),
    "!~": ("!~", _regex, lambda a, b: not _matches(a, b)),
    "=~": ("=~", str.lower, _equals_ignoring_case),
    "!=~": ("!=~", str.lower, lambda a, b: not _equals_ignoring_case(a, b)),
    "~~": ("~~", _regex_ignoring_case, _matches),
    "!~~": ("!~~", _regex_ignoring_case, lambda a, b: not _matches(a, b)),
    "<": ("<", _unchanged, operator.lt),
    ">=": (">=", _unchanged, operator.ge),
    ">": (">", _unchanged, operator.gt),
    "<=": ("<=", _unchanged, operator.le),
    "in": ("in", _lowered_set, filter_operator_in),
}


# The column, the operator and the argument, split like Livestatus does: Only ASCII
# whitespace separates them, and it isn't part of the argument's start. With re.ASCII,
# \s is exactly _ASCII_WHITESPACE.
_FILTER_LINE = re.compile(r"\s*(\S+)\s+(\S+)\s*(.*)", re.ASCII | re.DOTALL)


def _operator(name: str) -> _Operator:
    if (op := _filter_operators.get(name)) is None:
        raise MKClientError(f"Unknown filter operator '{name}'")
    return op


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
        self._parse_header_lines(raw_query, logger)

    def _parse_header_lines(self, raw_query: list[str], logger: Logger) -> None:
        for line in raw_query[1:]:
            try:
                header, argument = line.split(":", 1)
                self._parse_header_line(header, argument.lstrip(_ASCII_WHITESPACE), logger)
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
            self.requested_columns = _ascii_split(argument)
        elif header == "Filter":
            self.filters.append(self._parse_filter(argument))
        elif header == "Limit":
            self.limit = int(argument)
        else:
            logger.info("Ignoring not-implemented header %(header)s", {"header": header})

    def _parse_filter(self, textspec: str) -> QueryFilter:
        """Examples:
        id = 17
        name ~ This is some .* text
        host_name =

        Like in Livestatus, only ASCII whitespace separates the parts, so the argument
        keeps other whitespace of Python at its start, e.g. a no-break space."""
        if (match := _FILTER_LINE.fullmatch(textspec)) is None:
            raise MKClientError(f"Invalid filter: {textspec}")
        column, operator_name, raw_argument = match[1], match[2], match[3]

        try:
            convert = self.table.column_types[column]
        except KeyError as e:
            raise MKClientError(
                f"Unknown column: {column} (Available are: {self.table.column_names})"
            ) from e

        op_name, prepare, compare = _operator(operator_name)
        # TODO: BUG: The query is decoded to unicode after receiving it from
        # the socket. The columns with type str (initialized with "") will apply
        # str(argument) here and convert the value back to str! This will crash
        # when the filter contains non ascii characters!
        # Fix this by making the default values unicode and skip unicode conversion
        # here (for performance reasons) because argument is already unicode.
        # TODO: Fix the typing chaos below!
        argument = (
            [convert(arg) for arg in _ascii_split(raw_argument)]  # type: ignore[call-arg]
            if op_name == "in"
            else convert(raw_argument)  # type: ignore[call-arg]
        )
        # Prepared once instead of for each row. A regex fails to compile now instead of
        # in the middle of the reply, where the client can't tell a failure from its end.
        prepared = prepare(argument)

        return QueryFilter(
            column_name=column,
            operator_name=op_name,
            predicate=lambda x: compare(x, prepared),
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

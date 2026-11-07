#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"


import abc
import math
import operator
import re
import string
from collections.abc import Callable, Iterable, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from logging import Logger
from typing import Any, ClassVar, Literal, override

from cmk.ccc.exceptions import MKException

from .regex_translation import case_folded


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
# - add it to TIME_COLUMNS or LIST_COLUMNS below if Livestatus has it as a time or
#   a list column
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


def _first_argument(text: str) -> str:
    """The first of the arguments separated by ASCII whitespace, like in Livestatus"""
    return (_ascii_split(text) or [""])[0]


def _non_negative_integer(text: str) -> int:
    """Like nextNonNegativeIntegerArgument() of Livestatus, which uses std::from_chars(): An
    optional minus and ASCII digits, at most 2**31 - 1 and not negative. int() takes e.g.
    "+1", "1_000" or "\\u0661", too, but at most 4300 digits, even with leading zeros."""
    digits = text.removeprefix("-").lstrip("0")
    if (
        re.fullmatch("-?[0-9]+", text) is None
        or len(digits) > 10
        or not 0 <= (value := int(digits or "0") * (-1 if text.startswith("-") else 1)) < 2**31
    ):
        raise MKClientError(f"Expected a non-negative integer instead of '{text}'")
    return value


# With re.ASCII, \s is exactly _ASCII_WHITESPACE.
_ATOI = re.compile(r"\s*([+-]?)([0-9]+)", re.ASCII)


def _int32(number: int) -> int:
    """Like strtol() clamps a number to 64 bits and a conversion to int32_t keeps its lower
    32 bits, which Livestatus does for the values of filters and rows of int columns"""
    clamped = min(max(number, -(2**63)), 2**63 - 1)
    return (clamped + 2**31) % 2**32 - 2**31


def _atoi(text: str) -> int:
    """Like atoi() of glibc, which Livestatus uses for the values of int and time columns:
    The number at the start, else 0, as a 32-bit int."""
    if (match := _ATOI.match(text)) is None:
        return 0
    sign, digits = match[1], match[2].lstrip("0")
    # More digits are beyond the 64 bits anyway, and int() takes at most 4300.
    magnitude = int(digits or "0") if len(digits) <= 19 else 2**64
    return _int32(-magnitude if sign == "-" else magnitude)


_ATOF = re.compile(
    r"""\s*
    (?P<number>[+-]?(?:
        (?P<hex>0[xX](?:[0-9a-fA-F]+\.?[0-9a-fA-F]*|\.[0-9a-fA-F]+)(?:[pP][+-]?[0-9]+)?)
        | (?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?
        | [iI][nN][fF](?:[iI][nN][iI][tT][yY])?
        | [nN][aA][nN](?:\([0-9a-zA-Z_]*\))?
    ))""",
    re.VERBOSE | re.ASCII,
)


def _atof(text: str) -> float:
    """Like atof() of glibc in the C locale, which Livestatus uses for the values of double
    columns: The number at the start, also hexadecimal, infinite or NaN, else 0"""
    if (match := _ATOF.match(text)) is None:
        return 0.0
    number = match["number"]
    if match["hex"] is not None:
        try:
            return float.fromhex(number)
        except OverflowError:  # strtod() returns an infinity instead
            return float("-inf" if number.startswith("-") else "inf")
    return float(number.partition("(")[0])


# The float columns which Livestatus has as time columns, the others are double columns.
TIME_COLUMNS = frozenset(
    {"event_first", "event_last", "history_time", "status_replication_last_sync"}
)

# The columns which Livestatus has as list columns, see TableEventConsole*.cc. Their
# filters work like in Livestatus, see _list_predicate().
LIST_COLUMNS = frozenset(
    {
        "event_contact_groups",
        "event_match_groups",
        "event_match_groups_syslog_application",
        "status_event_limit_active_hosts",
        "status_event_limit_active_rules",
    }
)


def _filter_value(column_name: str, column_type: type[Any], text: str) -> object:
    """Converts the value of a filter like Livestatus, which has our bool columns as int
    columns, parses numbers via atoi() and atof(), and takes the value of a list column
    as it is"""
    if column_name in LIST_COLUMNS:
        return text
    if issubclass(column_type, int):
        return _atoi(text)
    if issubclass(column_type, float):
        return _atoi(text) if column_name in TIME_COLUMNS else _atof(text)
    return column_type(text)


def _int_of_row(value: object) -> object:
    """Like Livestatus gets an int or a bool from us: via atol() as an int32_t"""
    return _int32(value) if isinstance(value, int) else value


def _time_of_row(value: object) -> object:
    """Like Livestatus gets a time from us: as a time_t, i.e. truncated to an integer"""
    return int(value) if isinstance(value, float) and math.isfinite(value) else value


def _row_value(column_name: str, column_type: type[Any]) -> Callable[[object], object] | None:
    """How to make the value of a row like the one of Livestatus for comparing it with the
    value of a filter, None if it is the same already"""
    if issubclass(column_type, int):
        return _int_of_row
    if issubclass(column_type, float) and column_name in TIME_COLUMNS:
        return _time_of_row
    return None


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


def _case_folded_set(arguments: Iterable[str]) -> AbstractSet[str]:
    return {case_folded(argument) for argument in arguments}


def _regex(argument: str) -> re.Pattern[str]:
    return re.compile(argument)


def _regex_ignoring_case(argument: str) -> re.Pattern[str]:
    return re.compile(argument, re.IGNORECASE)


def filter_operator_in(a: str | None, b: AbstractSet[str]) -> bool:
    """Whether a is in b ignoring case like =~, where b is case-folded, see _case_folded_set().
    A regex with IGNORECASE would be slower. A missing value is in no set, see _matches()."""
    return a is not None and case_folded(a) in b


# None stands for a missing value, which neither matches nor equals anything, so
# the negated operators select it, just like operator.ne does.
def _matches(value: str | None, regex: re.Pattern[str]) -> bool:
    return value is not None and regex.search(value) is not None


# Unlike str.lower(), case_folded() folds e.g. "µ" and "μ" or "ſ" and "s" together, like RE2
# does for Livestatus. It even folds a bit more, e.g. "ı" and "i", so Livestatus forwards only
# =~ to us, not !=~.
def _equals_ignoring_case(value: str | None, folded: str) -> bool:
    return value is not None and case_folded(value) == folded


# A missing value isn't ordered either, so no ordering operator selects it, not even "!<",
# which is just another name for ">=". That's like NULL in SQL, e.g. in the SQLite history.
def _less(value: Any, argument: Any) -> bool:
    return value is not None and value < argument


def _less_or_equal(value: Any, argument: Any) -> bool:
    return value is not None and value <= argument


def _greater(value: Any, argument: Any) -> bool:
    return value is not None and value > argument


def _greater_or_equal(value: Any, argument: Any) -> bool:
    return value is not None and value >= argument


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
    "=~": ("=~", case_folded, _equals_ignoring_case),
    "!=~": ("!=~", case_folded, lambda a, b: not _equals_ignoring_case(a, b)),
    "~~": ("~~", _regex_ignoring_case, _matches),
    "!~~": ("!~~", _regex_ignoring_case, lambda a, b: not _matches(a, b)),
    "<": ("<", _unchanged, _less),
    ">=": (">=", _unchanged, _greater_or_equal),
    ">": (">", _unchanged, _greater),
    "<=": ("<=", _unchanged, _less_or_equal),
    # aliases of Livestatus
    "!<": (">=", _unchanged, _greater_or_equal),
    "!>=": ("<", _unchanged, _less),
    "!>": ("<=", _unchanged, _less_or_equal),
    "!<=": (">", _unchanged, _greater),
    # Unlike the other operators, Livestatus doesn't know this one.
    "in": ("in", _case_folded_set, filter_operator_in),
}


# The operators which only string columns have, see _parse_filter(). List columns have
# their own, see _list_predicate().
_STRING_OPERATORS = frozenset({"~", "!~", "=~", "!=~", "~~", "!~~", "in"})


TimeCondition = tuple[Literal["<", "<=", ">", ">="], int]


def _truncated_at_least(value: int) -> TimeCondition:
    """The condition on a time for being at least the value when truncated"""
    return (">=", value) if value > 0 else (">", value - 1)


def _truncated_less_than(value: int) -> TimeCondition:
    """The condition on a time for being less than the value when truncated"""
    return ("<", value) if value > 0 else ("<=", value - 1)


def time_conditions(operator_name: OperatorName, value: int) -> list[TimeCondition]:
    """The conditions on a time which hold together exactly when the time truncated to an
    integer, like Livestatus has it, satisfies a filter with the operator and the value. For
    the histories, which filter times themselves. For !=, they are the conditions for =."""
    match operator_name:
        case "=" | "!=":
            return [_truncated_at_least(value), _truncated_less_than(value + 1)]
        case ">=":
            return [_truncated_at_least(value)]
        case ">":
            return [_truncated_at_least(value + 1)]
        case "<":
            return [_truncated_less_than(value)]
        case "<=":
            return [_truncated_less_than(value + 1)]
        case _:
            raise ValueError(f"Operator '{operator_name}' not implemented for time columns")


def _list_elements(value: object) -> Sequence[object]:
    """The elements of a value of a list column like Livestatus gets them: None and a missing
    value ("") have none, and a last empty string is lost, see quote_tab() in cmk.ec.history
    and ec::split_list() of Livestatus."""
    if isinstance(value, str) or not isinstance(value, Iterable):
        return ()
    # No copy for the usual lists and tuples, this runs for every event.
    elements = value if isinstance(value, Sequence) else tuple(value)
    return elements[:-1] if elements and elements[-1] == "" else elements


def _has_element(value: object, predicate: Callable[[str], object]) -> bool:
    return any(isinstance(e, str) and predicate(e) for e in _list_elements(value))


def _list_predicate(operator_name: OperatorName, argument: str) -> Callable[[object], bool]:
    """Filters a list column like ListFilter of Livestatus: = and != test only whether the
    list is empty, >= and <= whether it contains the argument, <= ignoring case, < and >
    the opposite, the regex operators whether an element matches, and =~ and !=~ never
    hold. There's no "in" for list columns."""
    match operator_name:
        case "=":
            return lambda value: argument == "" and not _has_element(value, lambda _e: True)
        case "!=":
            return lambda value: argument == "" and _has_element(value, lambda _e: True)
        case ">=":
            return lambda value: _has_element(value, lambda e: e == argument)
        case "<":
            return lambda value: not _has_element(value, lambda e: e == argument)
        case "<=" | ">":
            folded = case_folded(argument)
            contained = operator_name == "<="
            return lambda value: (
                _has_element(value, lambda e: case_folded(e) == folded) == contained
            )
        case "~" | "!~" | "~~" | "!~~":
            flags = re.IGNORECASE if operator_name in {"~~", "!~~"} else re.NOFLAG
            search = re.compile(argument, flags).search
            matching = operator_name in {"~", "~~"}
            return lambda value: _has_element(value, search) == matching
        case "=~" | "!=~":
            return lambda _value: False
        case "in":
            raise MKClientError("The operator 'in' is not implemented for list columns")


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
        self.requested_columns: list[str] = []
        # NOTE: history's _get_mongodb and _get_files access filters and limits directly.
        self.filters: list[QueryFilter] = []
        self.limit: int | None = None
        self._parse_header_lines(raw_query)
        # Like in Livestatus, no columns at all means all of them.
        if not self.requested_columns:
            self.requested_columns = self.table.column_names

    def _parse_header_lines(self, raw_query: list[str]) -> None:
        for line in raw_query[1:]:
            try:
                # Like in Livestatus, a line without a colon is a header without argument.
                header, _colon, argument = line.partition(":")
                self._parse_header_line(header, argument.lstrip(_ASCII_WHITESPACE))
            except Exception as e:
                raise MKClientError(f"Invalid header line '{line.rstrip()}'") from e

    def _parse_header_line(self, header: str, argument: str) -> None:
        if header == "OutputFormat":
            output_format = _first_argument(argument)
            if output_format not in {"python", "plain", "json"}:
                raise MKClientError(
                    f'Invalid output format "{output_format}" (allowed are: python, plain, json)'
                )
            self.output_format = output_format
        elif header == "Columns":
            # Like in Livestatus, the columns of several headers add up.
            self.requested_columns += _ascii_split(argument)
        elif header == "Filter":
            self.filters.append(self._parse_filter(argument))
        elif header == "Limit":
            self.limit = _non_negative_integer(_first_argument(argument))
        else:
            # Like Livestatus does for unknown headers, we reject the ones we don't
            # implement, e.g. "Or:", instead of answering something else than asked for.
            raise MKClientError(f"Undefined request header '{header}'")

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
            column_type = self.table.column_types[column]
        except KeyError as e:
            raise MKClientError(
                f"Unknown column: {column} (Available are: {self.table.column_names})"
            ) from e

        op_name, prepare, compare = _operator(operator_name)
        if (
            op_name in _STRING_OPERATORS
            and column not in LIST_COLUMNS
            and not issubclass(column_type, str)
        ):
            # Livestatus uses the regex operators as bit mask operators for int columns, and
            # they select nothing for double columns. Fail now instead of in the middle of
            # the reply, where the client can't tell a failure from the end of the reply.
            raise MKClientError(f"Operator '{op_name}' not implemented for column '{column}'")
        # TODO: BUG: The query is decoded to unicode after receiving it from
        # the socket. The columns with type str (initialized with "") will apply
        # str(argument) here and convert the value back to str! This will crash
        # when the filter contains non ascii characters!
        # Fix this by making the default values unicode and skip unicode conversion
        # here (for performance reasons) because argument is already unicode.
        argument = (
            [_filter_value(column, column_type, arg) for arg in _ascii_split(raw_argument)]
            if op_name == "in"
            else _filter_value(column, column_type, raw_argument)
        )
        # Prepared once instead of for each row. A regex fails to compile now instead of
        # in the middle of the reply, where the client can't tell a failure from its end.
        prepared = prepare(argument) if column not in LIST_COLUMNS else None
        row_value = _row_value(column, column_type)
        predicate: Callable[[object], bool] = (
            _list_predicate(op_name, raw_argument)
            if column in LIST_COLUMNS
            else (lambda x: compare(x, prepared))
            if row_value is None
            else (lambda x: compare(row_value(x), prepared))
        )

        return QueryFilter(
            column_name=column,
            operator_name=op_name,
            predicate=predicate,
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

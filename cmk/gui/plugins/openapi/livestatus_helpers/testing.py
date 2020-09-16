#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module collects code which helps with testing Checkmk.

For code to be admitted to this module, it should itself be tested thoroughly, so we won't
have any friction during testing with these helpers themselves.

"""
import contextlib
import datetime as dt
import operator
import re
import time
from typing import Any, Callable, Dict, Generator, List, Literal, Optional, Tuple, Union

# TODO: Make livestatus.py a well tested package on pypi
# TODO: Move this code to the livestatus package
# TODO: Multi-site support. Need to have multiple lists of queries, one per site.

FilterFunc = Callable[[Dict[str, Any]], bool]
MatchType = Literal["strict", "ellipsis"]
OperatorFunc = Callable[[Any, Any], bool]
Response = List[List[Any]]


class MockLiveStatusConnection:
    """Mock a LiveStatus connection.

    NOTE:
        You probably want to use the fixture: cmk.gui.conftest:mock_livestatus

    This object can remember queries and the order in which they should arrive. Once the expected
    query was accepted the query is evaluated and a response is constructed from stored table data.

    It is up to the test-writer to set the appropriate queries and populate the table data.

    The class will verify that the expected queries (and _only_ those) are being issued
    in the `with` block. This means that:
         * Any additional query will trigger a RuntimeError
         * Any missing query will trigger a RuntimeError
         * Any mismatched query will trigger a RuntimeError
         * Any wrong order of queries will trigger a RuntimeError

    Args:
        report_multiple (bool):
            When set to True, this will potentially trigger mutliple Exceptions on __exit__. This
            can be useful when debugging chains of queries. Default is False.

    Examples:

        This test will pass:

            >>> live = (MockLiveStatusConnection()
            ...         .expect_query("GET hosts\\nColumns: name")
            ...         .expect_query("GET services\\nColumns: description"))
            >>> with live(expect_status_query=False):
            ...     live.query_non_parallel("GET hosts\\nColumns: name", '')
            ...     live.query_non_parallel("GET services\\nColumns: description",
            ...                             'ColumnHeaders: on')
            [['heute'], ['example.com']]
            [['description'], ['Memory'], ['CPU load'], ['CPU load']]

        This test will pass as well (useful in real GUI or REST-API calls):

            >>> live = MockLiveStatusConnection()
            >>> with live:
            ...     response = live.query_non_parallel(
            ...         ('GET status\\n'
            ...          'Cache: reload\\n'
            ...          'Columns: livestatus_version program_version program_start '
            ...          'num_hosts num_services'),
            ...         ''
            ...     )
            ...     # Response looks like [['2020-07-03', 'Check_MK 2020-07-03', 1593762478, 1, 36]]
            ...     assert len(response) == 1
            ...     assert len(response[0]) == 5

        This example will fail due to missing queries:

            >>> live = MockLiveStatusConnection()
            >>> with live():  # works either when called or not called
            ...      pass
            Traceback (most recent call last):
            ...
            RuntimeError: Expected queries were not queried:
             * 'GET status\\nCache: reload\\nColumns: livestatus_version program_version \
program_start num_hosts num_services'

        This example will fail due to a wrong query being issued:

            >>> live = MockLiveStatusConnection().expect_query("Hello\\nworld!")
            >>> with live(expect_status_query=False):
            ...     live.query_non_parallel("Foo\\nbar!", '')
            Traceback (most recent call last):
            ...
            RuntimeError: Expected query:
             * 'Hello\\nworld!'
            Got query:
             * 'Foo\\nbar!'

        This example will fail due to a superfluous query being issued:

            >>> live = MockLiveStatusConnection()
            >>> with live(expect_status_query=False):
            ...     live.query_non_parallel("Spanish inquisition!", '')
            Traceback (most recent call last):
            ...
            RuntimeError: Got unexpected query:
             * 'Spanish inquisition!'

    """
    def __init__(self, report_multiple: bool = False) -> None:
        self._prepend_site = False
        self._expected_queries: List[Tuple[str, List[str], List[List[str]], MatchType]] = []
        self._num_queries = 0
        self._query_index = 0
        self._report_multiple = report_multiple
        self._expect_status_query: Optional[bool] = None

        # We store some default values for some tables. May be expanded in the future.

        # Just that parse_check_mk_version is happy we replace the dashes with dots.
        _today = str(dt.datetime.utcnow().date()).replace("-", ".")
        _program_start_timestamp = int(time.time())
        self._tables: Dict[str, List[Dict[str, Any]]] = {
            'status': [{
                'livestatus_version': _today,
                'program_version': f'Check_MK {_today}',
                'program_start': _program_start_timestamp,
                'num_hosts': 1,
                'num_services': 36,
                'helper_usage_cmk': 0.00151953,
                'helper_usage_fetcher': 0.00151953,
                'helper_usage_checker': 0.00151953,
                'helper_usage_generic': 0.00151953,
                'average_latency_cmk': 0.0846039,
                'average_latency_generic': 0.0846039,
            }],
            'downtimes': [{
                'id': 54,
                'host_name': 'heute',
                'service_description': 'CPU load',
                'is_service': 1,
                'author': 'cmkadmin',
                'start_time': 1593770319,
                'end_time': 1596448719,
                'recurring': 0,
                'comment': 'Downtime for service',
            }],
            'hosts': [
                {
                    'name': 'heute',
                    'parents': ['example.com'],
                },
                {
                    'name': 'example.com',
                    'parents': [],
                },
            ],
            'services': [
                {
                    'host_name': 'example.com',
                    'description': 'Memory',
                },
                {
                    'host_name': 'example.com',
                    'description': 'CPU load',
                },
                {
                    'host_name': 'heute',
                    'description': 'CPU load',
                },
            ],
            'hostgroups': [
                {
                    'name': 'heute',
                    'members': ['heute'],
                },
                {
                    'name': 'example',
                    'members': ['example.com', 'heute'],
                },
            ],
            'servicegroups': [
                {
                    'name': 'heute',
                    'members': [['heute', 'Memory']],
                },
                {
                    'name': 'example',
                    'members': [
                        ['example.com', 'Memory'],
                        ['example.com', 'CPU load'],
                        ['heute', 'CPU load'],
                    ],
                },
            ],
        }

    def _expect_post_connect_query(self) -> None:
        # cmk.gui.sites._connect_multiple_sites asks for some specifics upon initial connection.
        # We expect this query and give the expected result.
        self.expect_query(
            [
                'GET status',
                'Cache: reload',
                'Columns: livestatus_version program_version program_start num_hosts num_services',
            ],
            force_pos=0,  # first query to be expected
        )

    def __call__(self, expect_status_query=True) -> 'MockLiveStatusConnection':
        self._expect_status_query = expect_status_query
        return self

    def __enter__(self) -> 'MockLiveStatusConnection':
        # This simulates a call to sites.live(). Upon call of sites.live(), the connection will be
        # ensured via _ensure_connected. This sends off a specific query to LiveStatus which we
        # expect to be called as the first query.
        if self._expect_status_query is None:
            self._expect_status_query = True

        if self._expect_status_query:
            self._expect_post_connect_query()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # We reset this, so the object can be re-used.
        self._expect_status_query = None
        if exc_type and not self._report_multiple:
            # In order not to confuse the programmer too much we skip the other collected
            # exceptions. This skip can be deactivated.
            return
        if self._expected_queries:
            remaining_queries = ""
            for query in self._expected_queries:
                remaining_queries += f"\n * {repr(query[0])}"
            raise RuntimeError(f"Expected queries were not queried:{remaining_queries}")

    def add_table(self, name: str, data: List[Dict[str, Any]]) -> 'MockLiveStatusConnection':
        """Add the data of a table.

        This is desirable in tests, to isolate the individual tests from one another. It is not
        recommended to use the global test-data for all the tests.

        Examples:

            If a table is set, the table is replaced.

                >>> host_list = [{'name': 'heute'}, {'name': 'gestern'}]

                >>> live = MockLiveStatusConnection()
                >>> _ = live.add_table('hosts', host_list)

            The table actually get's replaced, but only for this instance.

                >>> live._tables['hosts'] == host_list
                True

                >>> live = MockLiveStatusConnection()
                >>> live._tables['hosts'] == host_list
                False

        """
        self._tables[name] = data
        return self

    def expect_query(
        self,
        query: Union[str, List[str]],
        match_type: MatchType = 'strict',
        force_pos: Optional[int] = None,
    ) -> 'MockLiveStatusConnection':
        """Add a LiveStatus query to be expected by this class.

        This method is chainable, as it returns the instance again.

        Args:
            query:
                The expected query. May be a `str` or a list of `str` which, in the list case, will
                be joined by newlines.

            match_type:
                Flags with which to decide comparison behavior.
                Can be either 'strict' or 'ellipsis'. In case of 'ellipsis', the supplied query
                can have placeholders in the form of '...'. These placeholders are ignored in the
                comparison.

            force_pos:
                Only used internally. Ignore.

        Returns:
            The object itself, so you can chain.

        Raises:
            KeyError: when a table or a column used by the `query` is not defined in the test-data.

            ValueError: when an unknown `match_type` is given.

        """
        if match_type not in ('strict', 'ellipsis'):
            raise ValueError(f"match_type {match_type!r} not supported.")

        if isinstance(query, list):
            query = '\n'.join(query)

        table = _table_of_query(query)
        # If the columns are explicitly asked for, we get the columns here.
        columns = _column_of_query(query) or []

        if table and not columns:
            # Otherwise, we figure out the columns from the table store.
            for entry in self._tables.get(table, []):
                columns = sorted(entry.keys())

        # If neither table nor columns can't be deduced, we default to an empty response.
        result = []
        if table and columns:
            # We check the store for data and filter for the actual data that is requested.
            if table not in self._tables:
                raise KeyError(f"Table {table!r} not stored. Call .add_table(...)")
            result_dicts = evaluate_filter(query, self._tables[table])
            for entry in result_dicts:
                row = []
                for col in columns:
                    if col not in entry:
                        raise KeyError(f"Column '{table}.{col}' not known. "
                                       "Add to test-data or fix query.")
                    row.append(entry[col])
                result.append(row)

        if force_pos is not None:
            self._expected_queries.insert(force_pos, (query, columns, result, match_type))
        else:
            self._expected_queries.append((query, columns, result, match_type))

        return self

    def _lookup_next_query(self, query, headers: str) -> Response:
        if self._expect_status_query is None:
            raise RuntimeError("Please use MockLiveStatusConnection as a context manager.")

        # We don't want to str() cmk.gui.plugins.openapi.livestatus_helpers.queries.Query because
        # livestatus.py doesn't support it yet. We want it to crash if we ever get one here.
        if hasattr(query, 'default_suppressed_exceptions'):
            query = str(query)

        # TODO: This should be refactored to not be dependent on livestatus.py internal structure
        header_dict = _unpack_headers(headers)
        show_columns = header_dict.pop('ColumnHeaders', 'off')
        if header_dict:
            raise RuntimeError("The following headers are not yet supported: "
                               f"{', '.join(header_dict)}")

        if not self._expected_queries:
            raise RuntimeError(f"Got unexpected query:\n" f" * {repr(query)}")

        expected_query, columns, response, match_type = self._expected_queries[0]

        if not _compare(expected_query, query, match_type):
            raise RuntimeError(f"Expected query:\n"
                               f" * {repr(expected_query)}\n"
                               f"Got query:\n"
                               f" * {repr(query)}")

        # Passed, remove this entry.
        self._expected_queries.pop(0)

        def _generate_output():
            if show_columns == 'on':
                yield columns

            if self._prepend_site:
                yield from [['NO_SITE'] + line for line in response]
            else:
                yield from response

        return list(_generate_output())

    # Mocked livestatus api below
    def get_connection(self, site_id: str) -> 'MockLiveStatusConnection':
        return self

    def command(self, command: str, site: Optional[str] = 'local') -> None:
        self.do_command(command)

    def do_command(self, command: str) -> None:
        self._lookup_next_query(f"COMMAND {command}", '')

    def set_prepend_site(self, prepend_site: bool) -> None:
        self._prepend_site = prepend_site

    def query(self, query, headers='') -> Response:
        return self._lookup_next_query(query, headers)

    def query_parallel(self, query, headers) -> Response:
        return self._lookup_next_query(query, headers)

    def query_non_parallel(self, query, headers) -> Response:
        return self._lookup_next_query(query, headers)

    # SingleSiteConnection
    def do_query(self, query, add_headers: str = '') -> Response:
        return self._lookup_next_query(query, add_headers)


def _compare(pattern: str, string: str, match_type: MatchType) -> bool:
    """Compare two strings on different ways.

    Examples:
        >>> _compare("asdf", "asdf", "strict")
        True

        >>> _compare("...", "asdf", "ellipsis")
        True

        >>> _compare("...b", "abc", "ellipsis")
        False

        >>> _compare("foo", "asdf", "ellipsis")
        False

        >>> _compare("Hello ... world!", "Hello cruel world!", "ellipsis")
        True

        >>> _compare("COMMAND [...] DEL_FOO;", "COMMAND [123] DEL_FOO;", "ellipsis")
        True

    Args:
        pattern:
            The expected string.
            When `match_type` is set to 'ellipsis', may contain '...' for placeholders.

        string:
            The string to compare the pattern with.

        match_type:
            Strict comparisons or with placeholders.

    Returns:
        A boolean, indicating the match.

    """
    if match_type == 'strict':
        result = pattern == string
    elif match_type == 'ellipsis':
        final_pattern = pattern.replace("[", "\\[").replace("...", ".*?")  # non-greedy match
        result = bool(re.match(f"^{final_pattern}$", string))
    else:
        raise RuntimeError(f"Unsupported match behaviour: {match_type}")

    return result


@contextlib.contextmanager
def simple_expect(
    query='',
    match_type: MatchType = "ellipsis",
    expect_status_query=False,
) -> Generator[MockLiveStatusConnection, None, None]:
    """A simplified testing context manager.

    Args:
        query:
            A livestatus query.

        match_type:
            Either 'strict' or 'ellipsis'. Default is 'ellipsis'.

        expect_status_query:
            If the query of the status table (which Checkmk does when calling sites.live()) should
            be expected. Defaults to False.

    Returns:
        A context manager.

    Examples:

        >>> with simple_expect("GET hosts") as _live:
        ...    _ = _live.do_query("GET hosts")

    """
    live = MockLiveStatusConnection()
    if query:
        live.expect_query(query, match_type=match_type)
    with live(expect_status_query=expect_status_query):
        yield live


def evaluate_filter(query: str, result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter a list of dictionaries according to the filters of a LiveStatus query.

    The filters will be extracted from the query. And: and Or: directives are also supported.

    Currently only standard "Filter:" directives are supported, not StatsFilter: etc.

    Args:
        query:
            A LiveStatus query as a string.

        result:
            A list of dictionaries representing a LiveStatus table. The keys need to match the
            columns of the LiveStatus query. A mismatch will lead to, at least, a KeyError.

    Examples:

        >>> q = "GET hosts\\nFilter: name = heute"
        >>> data = [{'name': 'heute', 'state': 0}, {'name': 'morgen', 'state': 1}]
        >>> evaluate_filter(q, data)
        [{'name': 'heute', 'state': 0}]

        >>> q = "GET hosts\\nFilter: name = heute\\nFilter: state > 0\\nAnd: 2"
        >>> evaluate_filter(q, data)
        []

        >>> q = "GET hosts\\nFilter: name = heute\\nFilter: state = 0\\nAnd: 2"
        >>> evaluate_filter(q, data)
        [{'name': 'heute', 'state': 0}]

        >>> q = "GET hosts\\nFilter: name = heute\\nFilter: state > 0\\nOr: 2"
        >>> evaluate_filter(q, data)
        [{'name': 'heute', 'state': 0}, {'name': 'morgen', 'state': 1}]

        >>> q = "GET hosts\\nFilter: name ~ heu"
        >>> evaluate_filter(q, data)
        [{'name': 'heute', 'state': 0}]

    Returns:
        The filtered list of dictionaries.

    """
    filters = []
    for line in query.split("\n"):
        if line.startswith("Filter:"):
            filters.append(make_filter_func(line))
        elif line.startswith(("And:", "Or:")):
            op, count_ = line.split(" ", 1)
            count = int(count_)
            filters, params = filters[:-count], filters[-count:]
            filters.append(COMBINATORS[op](params))

    if not filters:
        # No filtering requested. Dump all the data.
        return result

    if len(filters) > 1:
        raise ValueError(f"Got {len(filters)} filters, expected one. Forgot And/Or?")

    return [entry for entry in result if filters[0](entry)]


def and_(filters: List[FilterFunc]) -> FilterFunc:
    """Combines multiple filters via a logical AND.

    Args:
        filters:
            A list of filter functions.

    Returns:
        True if all filters return True, else False.

    Examples:

        >>> and_([lambda x: True, lambda x: False])({})
        False

        >>> and_([lambda x: True, lambda x: True])({})
        True

    """
    def _and_impl(entry: Dict[str, Any]) -> bool:
        return all([filt(entry) for filt in filters])

    return _and_impl


def or_(filters: List[FilterFunc]) -> FilterFunc:
    """Combine multiple filters via a logical OR.

    Args:
        filters:
            A list of filter functions.

    Returns:
        True if any of the filters returns True, else False

    Examples:

        >>> or_([lambda x: True, lambda x: False])({})
        True

        >>> or_([lambda x: False, lambda x: False])({})
        False

    """
    def _or_impl(entry: Dict[str, Any]) -> bool:
        return any([filt(entry) for filt in filters])

    return _or_impl


COMBINATORS: Dict[str, Callable[[List[FilterFunc]], FilterFunc]] = {
    'And:': and_,
    'Or:': or_,
}
"""A dict of logical combinator helper functions."""


def cast_down(op: OperatorFunc) -> OperatorFunc:
    """Cast the second argument to the type of the first argument, then compare.

    No explicit checking for compatibility is done. You'll get a ValueError or a TypeError
    (depending on the type) if such a cast is not possible.
    """
    def _casting_op(a: Any, b: Any) -> bool:
        t = type(a)
        return op(a, t(b))

    return _casting_op


def match_regexp(string_: str, regexp: str) -> bool:
    """

    Args:
        string_: The string to check.
        regexp: The regexp to use against the string.

    Returns:
        A boolean.

    Examples:

        >>> match_regexp("heute", "heu")
        True

        >>> match_regexp("heute", " heu")
        False

        >>> match_regexp("heute", ".*")
        True

        >>> match_regexp("heute", "morgen")
        False

    """
    return bool(re.match(regexp, string_))


OPERATORS: Dict[str, OperatorFunc] = {
    '=': cast_down(operator.eq),
    '>': cast_down(operator.gt),
    '<': cast_down(operator.lt),
    '>=': cast_down(operator.le),
    '<=': cast_down(operator.ge),
    '~': match_regexp,
}
"""A dict of all implemented comparison operators."""


def make_filter_func(line: str) -> FilterFunc:
    """Make a filter-function from a LiveStatus-query filter row.

    Args:
        line:
            A LiveStatus filter row.

    Returns:
        A function which checks an entry against the filter.

    Examples:

        Check for some concrete values:

            >>> f = make_filter_func("Filter: name = heute")
            >>> f({'name': 'heute'})
            True

            >>> f({'name': 'morgen'})
            False

            >>> f({'name': ' heute '})
            False

        Check for empty values:

            >>> f = make_filter_func("Filter: name = ")
            >>> f({'name': ''})
            True

            >>> f({'name': 'heute'})
            False

        If not implemented, yell:

            >>> f = make_filter_func("Filter: name !! heute")
            Traceback (most recent call last):
            ...
            ValueError: Operator '!!' not implemented. Please check docs or implement.


    """
    field, op, *value = line[7:].split(None, 2)  # strip Filter: as len("Filter:") == 7
    if op not in OPERATORS:
        raise ValueError(f"Operator {op!r} not implemented. Please check docs or implement.")

    # For checking empty values. In this case an empty list.
    if not value:
        value = ['']

    def _apply_op(entry: Dict[str, Any]) -> bool:
        return OPERATORS[op](entry[field], *value)

    return _apply_op


def _column_of_query(query: str) -> Optional[List[str]]:
    """Figure out the queried columns from a LiveStatus query.

    Args:
        query:
            A LiveStatus query as a string.

    Returns:
        A list of column names referenced by the query.

    Examples:

        >>> _column_of_query('GET hosts\\nColumns: name status alias\\nFilter: name = foo')
        ['name', 'status', 'alias']

        >>> _column_of_query('GET hosts\\nFilter: name = foo')

    """
    for line in query.split("\n"):
        if line.startswith('Columns:'):
            return line[8:].split()  # len("Columns:") == 8

    return None


def _table_of_query(query: str) -> Optional[str]:
    """Figure out a table from a LiveStatus query.

    Args:
        query:
            A LiveStatus query as a string.

    Returns:
        The table name referenced by the LiveStatus query.

    Examples:

        >>> _table_of_query("GET hosts\\nColumns: name\\nFilter: name = foo")
        'hosts'

        >>> _table_of_query("GET     hosts\\nColumns: name\\nFilter: name = foo")
        'hosts'

        >>> _table_of_query("GET\\n")

    """
    lines = query.split("\n")
    if lines and lines[0].startswith("GET "):
        return lines[0].split(None, 1)[1]

    return None


def _unpack_headers(headers: str) -> Dict[str, str]:
    r"""Unpack and normalize headers from a string.

    Examples:

        >>> _unpack_headers("ColumnHeaders: off")
        {'ColumnHeaders': 'off'}

        >>> _unpack_headers("ColumnHeaders: off\nResponseFormat: fixed16")
        {'ColumnHeaders': 'off', 'ResponseFormat': 'fixed16'}

    Args:
        headers:
            Headers as a string.

    Returns:
        Headers as a dict.

    """
    unpacked = {}
    for header in headers.split("\n"):
        if not header:
            continue
        key, value = header.split(":", 1)
        unpacked[key] = value.lstrip(" ")
    return unpacked

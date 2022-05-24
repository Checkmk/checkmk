#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module collects code which helps with testing Checkmk.

For code to be admitted to this module, it should itself be tested thoroughly, so we won't
have any friction during testing with these helpers themselves.

"""
from __future__ import annotations

import collections
import datetime as dt
import io
import itertools
import json
import operator
import re
import socket
import statistics
import time
from typing import Any, Callable, Dict, List, Literal, Mapping, Optional, Tuple, Union

from livestatus import LivestatusTestingError

# TODO: Make livestatus.py a well tested package on pypi
# TODO: Move this code to the livestatus package

MatchType = Literal["strict", "ellipsis", "loose"]
Operator = str
OperatorFunc = Callable[[Any, Any], bool]
Response = List[List[Any]]
ResultEntry = Dict[str, Any]
ResultList = List[ResultEntry]
FilterKeyFunc = Callable[[ResultEntry], bool]
ReduceFunc = Callable[[List[Any]], Any]
# TODO: Integrate NewType into the internal interfaces.
SiteName = str  # NewType("SiteName", str)
ColumnName = str  # NewType("ColumnName", str)
TableName = str  # NewType("TableName", str)
Tables = Dict[TableName, Dict[SiteName, ResultList]]


def repr2(obj):
    """Create a string representation of an object like in Python2

    Examples:

        >>> repr2({b"Hallo": "Welt"})
        "{'Hallo': u'Welt'}"

        >>> repr2(b"Hallo Welt")
        "'Hallo Welt'"

        >>> repr2("Hallo Welt")
        "u'Hallo Welt'"

        >>> repr2({"1": "a", "2": "b"})
        "{u'1': u'a', u'2': u'b'}"

        >>> repr2([1, 2, 3])
        '[1, 2, 3]'

    Args:
        obj:
            The object to be serialized.

    Returns:
        A string representation of the object, like Python2 would do.

    """
    if isinstance(obj, dict):  # pylint: disable=no-else-return
        return "{" + ", ".join(f"{repr2(k)}: {repr2(v)}" for k, v in obj.items()) + "}"
    elif isinstance(obj, (list, tuple)):
        return "[" + ", ".join(repr2(x) for x in obj) + "]"
    elif isinstance(obj, str):
        return f"u'{obj}'"
    elif isinstance(obj, bytes):
        return f"'{obj.decode('utf-8')}'"
    else:
        return repr(obj)


class FakeSocket:
    def __init__(self, mock_live: MockSingleSiteConnection) -> None:
        self.mock_live = mock_live
        (self._write_socket, self._read_socket) = socket.socketpair()
        # The fake socket always states that there is something to read
        # (otherwise, select/poll calls on this fake socket will run into a timeout)
        # The actual (fake) data is not send/received via this FakeSocket fds, anyway
        self._write_socket.send(b"This could be your data")

    def settimeout(self, timeout: Optional[int]) -> None:
        pass

    def connect(self, address: str) -> None:
        pass

    def fileno(self):
        return self._read_socket.fileno()

    def close(self):
        return

    def recv(self, length: int) -> bytes:
        return self.mock_live.socket_recv(length)

    def send(self, data: bytes) -> None:
        return self.mock_live.socket_send(data)

    def sendall(self, data: bytes) -> None:
        return self.mock_live.socket_send(data)


def _make_livestatus_response(response: Response, output_format: str) -> str:
    """Build a (almost) convincing LiveStatus response

    Special response headers (except OutputFormat) are not honored yet.

    >>> resp = [['foo', b"bar"], [1, {}]]

    >>> _make_livestatus_response(resp, "json")
    '200          25\\n[["foo", "bar"], [1, {}]]'

    >>> _make_livestatus_response(resp, "python")
    "200          26\\n[[u'foo', 'bar'], [1, {}]]"

    >>> _make_livestatus_response(resp, "python3")
    "200          26\\n[['foo', b'bar'], [1, {}]]"

    >>> _make_livestatus_response(resp, "json")[:16]
    '200          25\\n'

    Args:
        response:
            Some python struct.

    Returns:
        The fake LiveStatus response as a string.

    """
    if output_format == "json":
        # NOTE:
        #   need to ensure bytes are also strings, because json.dumps will throw an ValueError
        #   otherwise. I assume they are encoded as utf-8.
        response = [
            [x.decode("utf-8") if isinstance(x, bytes) else x for x in row] for row in response
        ]
        data = json.dumps(response)
    elif output_format == "python":
        data = repr2(response)
    elif output_format == "python3":
        data = repr(response)
    else:
        raise ValueError(f"Unknown output format: {output_format}")

    code = 200
    length = len(data)
    return f"{code:<3} {length:>11}\n{data}"


class MockLiveStatusConnection:
    """Mock a LiveStatus connection.

    NOTE:
        You probably want to use the fixture: cmk.gui.conftest:mock_livestatus

    This object can remember queries and the order in which they should arrive. Once the expected
    query was accepted the query is evaluated and a response is constructed from stored table data.

    It is up to the test-writer to set the appropriate queries and populate the table data.

    The class will verify that the expected queries (and _only_ those) are being issued
    in the `with` block. This means that:
         * Any additional query will trigger a LivestatusTestingError
         * Any missing query will trigger a LivestatusTestingError
         * Any mismatched query will trigger a LivestatusTestingError
         * Any wrong order of queries will trigger a LivestatusTestingError

    Examples:

        This test will pass:

            >>> live = MockLiveStatusConnection()
            >>> _ = live.expect_query("GET hosts\\nColumns: name")
            >>> with live(expect_status_query=False):
            ...     live.result_of_next_query("GET hosts\\nColumns: name")[0]
            [['heute'], ['example.com']]

            >>> _ = live.expect_query("GET services\\nColumns: description\\nColumnHeaders: on")
            >>> with live(expect_status_query=False):
            ...     live.result_of_next_query(
            ...         "GET services\\nColumns: description\\nColumnHeaders: on")[0]
            [['description'], ['Memory'], ['CPU load'], ['CPU load']]

        This test will pass as well (useful in real GUI or REST-API calls):

            >>> live = MockLiveStatusConnection()
            >>> with live:
            ...     response = live.result_of_next_query(
            ...         'GET status\\n'
            ...         'Columns: livestatus_version program_version program_start '
            ...         'num_hosts num_services core_pid'
            ...     )[0]
            ...     # Response looks like [['2020-07-03', 'Check_MK 2020-07-03', 1593762478, 1, 36]]
            ...     assert len(response) == 1
            ...     assert len(response[0]) == 6

        Some Stats calls are supported as well:

            >>> live = MockLiveStatusConnection()
            >>> _ = live.expect_query("GET hosts\\nColumns: filename\\nStats: state > 0")
            >>> with live(expect_status_query=False):
            ...     live.result_of_next_query(
            ...         'GET hosts\\n'
            ...         'Cache: reload\\n'
            ...         'Columns: filename\\n'
            ...         'Stats: state > 0'
            ...     )[0]
            [['/wato/hosts.mk', 1]]

        This example will fail due to missing queries:

            >>> live = MockLiveStatusConnection()
            >>> with live():  # works either when called or not called
            ...      pass
            Traceback (most recent call last):
            ...
            livestatus.LivestatusTestingError: Expected queries were not queried on site 'NO_SITE':
             * 'GET status\\nColumns: livestatus_version program_version \
program_start num_hosts num_services core_pid'

        This example will fail due to a wrong query being issued:

            >>> live = MockLiveStatusConnection().expect_query("Hello world!")
            >>> with live(expect_status_query=False):
            ...     live.result_of_next_query("Foo bar!")
            Traceback (most recent call last):
            ...
            livestatus.LivestatusTestingError: Expected query (strict) on site 'NO_SITE':
             * 'Hello world!'
            Got query:
             * 'Foo bar!'

        This example will fail due to a superfluous query being issued:

            >>> live = MockLiveStatusConnection()
            >>> with live(expect_status_query=False):
            ...     live.result_of_next_query("Spanish inquisition!")
            Traceback (most recent call last):
            ...
            livestatus.LivestatusTestingError: Got unexpected query on site 'NO_SITE':
             * 'Spanish inquisition!'

        Using the new site parameter, we can add data to specific sites.

            >>> conn = MockLiveStatusConnection()
            >>> _ = conn.expect_query("GET hosts")

            >>> len(conn.result_of_next_query("GET hosts")[0])
            2

            >>> _ = conn.expect_query("GET hosts\\nColumns: name\\nColumnHeaders: on")
            >>> conn.result_of_next_query("GET hosts\\nColumns: name\\nColumnHeaders: on")[0]
            [['name'], ['heute'], ['example.com']]

            >>> conn.add_table('hosts', [{'name': 'morgen'}], site='remote')

            >>> _ = conn.expect_query("GET hosts\\nColumns: name\\nColumnHeaders: on")
            >>> conn.result_of_next_query("GET hosts\\nColumns: name\\nColumnHeaders: on")[0]
            [['name'], ['heute'], ['example.com'], ['morgen']]

    """

    def __init__(self) -> None:
        self.sites: List[SiteName] = []
        self._connections: Dict[SiteName, MockSingleSiteConnection] = collections.OrderedDict()
        self._expect_status_query: Optional[bool] = None
        self.tables: Tables = {}
        self.set_sites(["NO_SITE", "remote", "local"])

    def set_sites(self, site_names: List[ColumnName]) -> None:
        """Set a new list of sites to be queried.

        NOTE: This resets all table data to the default data.

        Args:
            site_names:
                A list of site names.

        """
        self.sites = site_names
        self.tables.clear()
        for table_name, table in _default_tables().items():
            self.add_table(table_name, table)

    @property
    def connections(self) -> Mapping[SiteName, MockSingleSiteConnection]:
        for site_name in self.sites:
            if site_name not in self._connections:
                self._connections[site_name] = MockSingleSiteConnection(site_name, self)
        return self._connections

    def create_socket(self, family, site_name: Optional[SiteName]):
        if site_name is None:  # plain SingleConnection instantiated by hand
            site_name = self.sites[0]
        return self.connections[site_name].socket

    def result_of_next_query(self, query: str) -> tuple[Response, str]:
        result = []
        single_conn: MockSingleSiteConnection
        show_columns = _show_columns(query)
        output_format = pick_header(query, "OutputFormat", "json")
        for conn_number, single_conn in enumerate(self.connections.values(), start=0):
            for row_number, row in enumerate(single_conn.result_of_next_query(query)[0], start=0):
                # We only want to see the column descriptions once. For all the other sites,
                # we skip these.
                if show_columns and conn_number > 0 and row_number == 0:
                    continue

                # We skip empty lists which signal "nothing found" from a site.
                if not row:
                    continue

                result.append(row)

        return result, output_format

    def enabled_and_disabled_sites(self, user_id) -> Tuple[dict, dict]:
        """This method is used to inject the currently configured sites into livestatus.py"""
        return {site_name: {"socket": "unix:"} for site_name in self.sites}, {}

    def __call__(self, expect_status_query=True) -> MockLiveStatusConnection:
        self._expect_status_query = expect_status_query
        return self

    def __enter__(self) -> MockLiveStatusConnection:
        # This simulates a call to sites.live(). Upon call of sites.live(), the connection will be
        # ensured via _ensure_connected. This sends off a specific query to LiveStatus which we
        # expect to be called as the first query.
        if self._expect_status_query is None:
            self._expect_status_query = True

        if self._expect_status_query:
            # cmk.gui.sites._connect_multiple_sites asks for some specifics upon initial connection.
            # We expect this query and give the expected result.
            query = [
                "GET status",
                "Columns: livestatus_version program_version program_start num_hosts num_services core_pid",
            ]
            self.expect_query(query, force_pos=0)  # first query to be expected

        for single_conn in self.connections.values():
            single_conn.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise
        for single_conn in self.connections.values():
            single_conn.__exit__(exc_type, exc_val, exc_tb)

    def add_table(
        self,
        table_name: TableName,
        table_data: ResultList,
        site: Optional[SiteName] = None,
    ) -> None:
        """Add the data of a table.

        This is desirable in tests, to isolate the individual tests from one another. It is not
        recommended using the global test-data for all the tests.

        Args:
            table_name:
                The name of the Livestatus table.

            table_data:
                A list of dicts where each dict represents a row of the table. The keys of the
                dicts represent the columns of the Livestatus table.

            site:
                Optionally a site where the table should be added. NOTE: When this is not given,
                it defaults to the FIRST SITE configured.

        Examples:

            If a table is set, the table is replaced.

                >>> host_list = [{'name': 'heute'}, {'name': 'gestern'}]
                >>> live = MockLiveStatusConnection()
                >>> live.set_sites(['local'])

                >>> _ = live.add_table('hosts', host_list)

            The table actually gets replaced, but only for this instance.

                >>> live.tables['hosts']['local'] == host_list
                True

                >>> live = MockLiveStatusConnection()
                >>> live.tables['hosts']['local'] == host_list
                False
        """
        if site and site not in self.sites:
            raise ValueError(f"Unknown site: {site!r}")
        if site is None:
            site = self.sites[0]
        self.tables.setdefault(table_name, {})
        for _site in self.sites:
            self.tables[table_name].setdefault(_site, [])
        self.tables[table_name][site] = table_data

    def expect_query(
        self,
        query: Union[str, List[str]],
        match_type: MatchType = "strict",
        force_pos: Optional[int] = None,
    ) -> MockLiveStatusConnection:
        """Add a LiveStatus query to be expected by this class.

        This method is chainable, as it returns the instance again.

        Args:
            query:
                The expected query. Maybe a `str` or a list of `str` which, in the list case, will
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
            ValueError: when an unknown `match_type` is given.
        """
        if isinstance(query, list):
            query = "\n".join(query)
        query = query.rstrip()

        if query.startswith("COMMAND"):
            first_conn = list(self.connections.values())[0]
            first_conn.expect_query(query, match_type, force_pos)
        else:
            for single_conn in self.connections.values():
                single_conn.expect_query(query, match_type, force_pos)
        return self


def execute_query(
    tables: Tables,
    query: str,
    site_name: SiteName,
) -> Tuple[Response, List[ColumnName]]:
    """Execute a Livestatus query against a dict of table data.

    This function will evaluate the query and gather the correct information
    from the tables it knows. It will then construct a list of lists Livestatus
    response.

    Args:
        tables:
            A dict where the key is the table name and the value is a list of dicts
            where each dict is a row of the column.

        query:
            A Livestatus query as a string.

        site_name:
            The site_name to pick the correct table data and construct better error messages.

    Returns:
        A list of lists
    """
    table = _table_of_query(query)
    # If the columns are explicitly asked for, we get the columns here.
    query_columns = _column_of_query(query) or []

    columns: List[ColumnName] = query_columns
    if table and not query_columns:
        # Otherwise, we figure out the columns from the table store.
        for entry in tables[table].get(site_name, []):
            columns[:] = sorted(entry.keys())
            break
    else:
        columns = query_columns

    # If neither table nor columns can't be deduced, we default to an empty response.
    result = []
    if table and columns:
        # We check the store for data and filter for the actual data that is requested.
        if table not in tables:
            raise LivestatusTestingError(
                f"Table {table!r} not stored on site {site_name!r}." " Call .add_table(...)"
            )

        # Filtering and Aggregating
        filtered_dicts = evaluate_filter(query, tables[table].get(site_name, []))
        result_dicts = evaluate_stats(query, query_columns, filtered_dicts)

        # Flatten the result for serialization.
        for entry in result_dicts:
            row = []
            for col in columns:
                try:
                    row.append(entry[col])
                except KeyError as exc:
                    raise KeyError(
                        f"Column '{col}' not in result. " "Add to test-data or fix query."
                    ) from exc

            for col in sorted(entry.keys()):
                if col.startswith("stat_"):
                    row.append(entry[col])
            result.append(row)

    return result, columns


def pick_header(query: str, header_name: str, default: Optional[str] = None) -> str:
    """Pick a header from a query.

    Examples:

        >>> pick_header("GET hosts", "OutputFormat", default="json")
        'json'

        >>> pick_header("GET hosts\\nOutputFormat: python", "OutputFormat")
        'python'

        >>> pick_header("GET hosts", "OutputFormat")
        Traceback (most recent call last):
        ...
        ValueError: Header OutputFormat not found in query.

    Args:
        query:
            A Livestatus query as a string.

        header_name:
            The name of the header to pick.

        default:
            The default value to return if the header is not found.

    Returns:
        The header value.
    """
    for line in query.splitlines():
        if line.startswith(header_name):
            return line.split(": ", 1)[1]

    if default is not None:
        return default

    raise ValueError(f"Header {header_name} not found in query.")


def remove_headers(query: str, headers: List[str]) -> str:
    """Remove specific Livestatus headers from a query

    Examples:

        >>> remove_headers("GET hosts\\nCache: reload\\nKeepalive: on", ['Cache', 'Keepalive'])
        'GET hosts'

    Args:
        query:
            The Livestatus query as a string

        headers:
            A list of Livestatus header names which shall be removed from this query.

    Returns:
        The query with the headers removed.

    """
    result = []
    for line in query.splitlines():
        header = line.split(": ", 1)[0]
        if header in headers:
            continue
        result.append(line)
    return "\n".join(result)


class MockSingleSiteConnection:
    def __init__(self, site_name, multisite_connection) -> None:
        self._site_name = site_name
        self._multisite = multisite_connection
        self._last_response: Optional[io.StringIO] = None
        self._expected_queries: List[Tuple[str, MatchType]] = []

        self.socket = FakeSocket(self)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={id(self)} site={self._site_name}>"

    def expect_query(
        self,
        query: Union[str, List[str]],
        match_type: MatchType = "strict",
        force_pos: Optional[int] = None,
    ) -> MockSingleSiteConnection:
        if match_type not in ("strict", "ellipsis", "loose"):
            raise ValueError(f"match_type {match_type!r} not supported.")

        if isinstance(query, list):
            query = "\n".join(query)

        if force_pos is not None:
            self._expected_queries.insert(force_pos, (query, match_type))
        else:
            self._expected_queries.append((query, match_type))
        return self

    def result_of_next_query(self, query: str) -> tuple[Response, str]:
        if not self._expected_queries:
            raise LivestatusTestingError(
                f"Got unexpected query on site {self._site_name!r}:" "\n" f" * {repr(query)}"
            )

        expected_query, match_type = self._expected_queries.pop(0)
        output_format = pick_header(query, "OutputFormat", "json")

        if query.startswith("GET "):
            # FIXME: Needs to be a bit more strict. We remove them on both sides to make the
            #        queries comparable.
            headers_to_remove = [
                "Cache",
                "Localtime",
                "OutputFormat",
                "KeepAlive",
                "ResponseHeader",
            ]
            expected_query = remove_headers(expected_query, headers_to_remove)
            query = remove_headers(query, headers_to_remove)

        if not _compare(expected_query, query, match_type):
            raise LivestatusTestingError(
                f"Expected query ({match_type}) on site {self._site_name!r}:\n"
                f" * {repr(expected_query)}\n"
                f"Got query:\n"
                f" * {repr(query)}"
            )

        def _generate_output():
            if query.startswith("COMMAND"):
                return
            _response, _columns = execute_query(self._multisite.tables, query, self._site_name)

            if _show_columns(query):
                yield _columns

            yield from _response

        return list(_generate_output()), output_format

    def socket_recv(self, length: int) -> bytes:
        if self._last_response is None:
            raise LivestatusTestingError("Nothing sent yet. Can't receive!")
        return self._last_response.read(length).encode("utf-8")

    def socket_send(self, data: bytes) -> None:
        if data[-2:] == b"\n\n":
            data = data[:-2]
        response, output_format = self.result_of_next_query(data.decode("utf-8"))
        self._last_response = io.StringIO(_make_livestatus_response(response, output_format))

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._expected_queries:
            remaining_queries = ""
            for query in self._expected_queries:
                remaining_queries += f"\n * {repr(query[0])}"
            raise LivestatusTestingError(
                f"Expected queries were not queried on site {self._site_name!r}:{remaining_queries}"
            )


def _show_columns(query: str) -> bool:
    header_dict = _unpack_headers(query)
    return header_dict.pop("ColumnHeaders", "off") == "on"


def _default_tables() -> Dict[TableName, ResultList]:
    # Just that parse_check_mk_version is happy we replace the dashes with dots.
    _today = str(dt.datetime.utcnow().date()).replace("-", ".")
    _program_start_timestamp = int(time.time())
    return {
        "status": [
            {
                "livestatus_version": _today,
                "program_version": f"Check_MK {_today}",
                "program_start": _program_start_timestamp,
                "num_hosts": 1,
                "num_services": 36,
                "helper_usage_cmk": 0.00151953,
                "helper_usage_fetcher": 0.00151953,
                "helper_usage_checker": 0.00151953,
                "helper_usage_generic": 0.00151953,
                "average_latency_cmk": 0.0846039,
                "average_latency_fetcher": 0.0846039,
                "average_latency_generic": 0.0846039,
                "core_pid": 12345,
            }
        ],
        "downtimes": [
            {
                "id": 54,
                "host_name": "heute",
                "service_description": "CPU load",
                "is_service": 1,
                "author": "cmkadmin",
                "start_time": 1593770319,
                "end_time": 1596448719,
                "recurring": 0,
                "comment": "Downtime for service",
            }
        ],
        "hosts": [
            {
                "name": "heute",
                "parents": ["example.com"],
                "filename": "/wato/hosts.mk",
                "state": 1,
            },
            {
                "name": "example.com",
                "parents": [],
                "filename": "/wato/hosts.mk",
                "state": 0,
            },
        ],
        "services": [
            {
                "host_name": "example.com",
                "description": "Memory",
            },
            {
                "host_name": "example.com",
                "description": "CPU load",
            },
            {
                "host_name": "heute",
                "description": "CPU load",
            },
        ],
        "hostgroups": [
            {
                "name": "heute",
                "members": ["heute"],
            },
            {
                "name": "example",
                "members": ["example.com", "heute"],
            },
        ],
        "servicegroups": [
            {
                "name": "heute",
                "members": [["heute", "Memory"]],
            },
            {
                "name": "example",
                "members": [
                    ["example.com", "Memory"],
                    ["example.com", "CPU load"],
                    ["heute", "CPU load"],
                ],
            },
        ],
    }


def _compare(expected: str, query: str, match_type: MatchType) -> bool:
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

        >>> _compare("GET hosts\\nColumns: name",
        ...          "GET hosts\\nCache: reload\\nColumns: name\\nLocaltime: 12345",
        ...          'loose')
        True

        >>> _compare("GET hosts\\nColumns: name",
        ...          "GET hosts\\nCache: reload\\nColumns: alias name\\nLocaltime: 12345",
        ...          'loose')
        False

    Args:
        expected:
            The expected string.
            When `match_type` is set to 'ellipsis', may contain '...' for placeholders.

        query:
            The string to compare the pattern with.

        match_type:
            Strict comparisons or with placeholders.

    Returns:
        A boolean, indicating the match.

    """
    if match_type == "loose":
        # FIXME: Too loose, needs to be more strict.
        #   "GET hosts" also matches "GET hosts\nColumns: ..." which should not be possible.
        string_lines = query.splitlines()
        for line in expected.splitlines():
            if line not in string_lines:
                result = False
                break
        else:
            result = True
    elif match_type == "strict":
        result = expected == query
    elif match_type == "ellipsis":
        final_pattern = expected.replace("[", "\\[").replace("...", ".*?")  # non-greedy match
        result = bool(re.match(f"^{final_pattern}$", query))
    else:
        raise LivestatusTestingError(f"Unsupported match behaviour: {match_type}")

    return result


def evaluate_stats(query: str, columns: List[ColumnName], result: ResultList) -> ResultList:
    """Aggregate the result set, as told by the Stats directives

    This function not only does counting and aggregating. It also groups the result by the
    individual distinct values.

    Examples:

        When no Stats directives are present, we pass through the result

            >>> evaluate_stats("", [], [{'state': 1}, {'state': 2}])
            [{'state': 1}, {'state': 2}]

        Whenever Stats directives are present, we evaluate and reduce the result

            >>> evaluate_stats("Stats: sum state", [], [{'state': 1}, {'state': 2}])
            [{'stat_1': 3}]

            >>> evaluate_stats("Stats: avg state", [], [{'state': 0}, {'state': 10}])
            [{'stat_1': 5}]

            >>> evaluate_stats("Stats: min state", [], [{'state': 0}, {'state': 10}])
            [{'stat_1': 0}]

            >>> evaluate_stats("Stats: max state", [], [{'state': 0}, {'state': 10}])
            [{'stat_1': 10}]

        Counting directives are also honored

            >>> evaluate_stats("Stats: state > 0", [], [{'state': 1}, {'state': 2}, {'state': 1}])
            [{'stat_1': 3}]

        Multiple counting directives are evaluated independently

            >>> evaluate_stats("Stats: state > 0\\nStats: state >= 2", [],
            ...                [{'state': 1}, {'state': 2}, {'state': 1}])
            [{'stat_1': 3}, {'stat_2': 1}]

        Combinations of counting directives are not yet implemented

            >>> evaluate_stats("Stats: state > 0\\nStats: state != 2\\nStatsAnd: 2", [],
            ...                [{'state': 1}, {'state': 2}, {'state': 1}])
            Traceback (most recent call last):
            ...
            livestatus.LivestatusTestingError: Stats combinators are not yet implemented!

        Non-contiguous results don't throw the grouper off-track.

            >>> evaluate_stats("Stats: state = 0", ['site'], [
            ...     {'site': 'a', 'state': 0},  # <- !
            ...     {'site': 'b', 'state': 0},
            ...     {'site': 'a', 'state': 1},  # <- !
            ...     {'site': 'b', 'state': 0},
            ...     {'site': 'b', 'state': 1},
            ... ])
            [{'site': 'a', 'stat_1': 1}, {'site': 'b', 'stat_1': 2}]

    Args:
        query:
            A livestatus query, with or without stats attached.

        columns:
            A list of columns as strings.

        result:
            A result set.

    Returns:
        A grouped result set.

    """
    reducers = []
    for line in query.splitlines():
        if line.startswith("Stats: "):
            reducers.append(make_reducer_func(line))
        elif line.startswith(("StatsAnd: ", "StatsOr: ", "StatsNegate: ")):
            raise LivestatusTestingError("Stats combinators are not yet implemented!")

    if not reducers:
        return result

    def key_func(entry):
        return tuple((field, entry[field]) for field in columns)

    aggregated = []
    if columns:
        # We group by all distinct field values explicitly referenced in Columns:
        for key, group in itertools.groupby(sorted(result, key=key_func), key=key_func):
            for count, reducer in enumerate(reducers, start=1):
                aggregated.append({**dict(key), f"stat_{count}": reducer(list(group))})
    else:
        for count, reducer in enumerate(reducers, start=1):
            aggregated.append({f"stat_{count}": reducer(result)})
    return aggregated


def make_reducer_func(line: str) -> ReduceFunc:
    """

    >>> make_reducer_func("Stats: avg field")([{'field': 1}, {'field': 6}])
    3.5

    >>> make_reducer_func("Stats: field = 1")([{'field': 1}, {'field': 1}])
    2

    >>> make_reducer_func("Stats: field >= 1")([{'field': 2}, {'field': 1}])
    2

    Args:
        line:

    Returns:

    """
    # As described in https://docs.checkmk.com/master/en/livestatus_references.html#stats
    aggregators: Dict[str, ReduceFunc] = {
        "avg": statistics.mean,
        "sum": sum,
        "min": min,
        "max": max,
        "std": statistics.stdev,
        "suminv": lambda x: 1 / sum(x),
        "avginv": lambda x: 1 / statistics.mean(x),
    }

    def _reducer(_func: ReduceFunc, make_value: Callable[[ResultEntry], Any]) -> ReduceFunc:
        def _reduce(result: List[Any]) -> Any:
            return _func([make_value(entry) for entry in result])

        return _reduce

    expr = line.split("Stats: ", 1)[1]
    parts = expr.split(None, 3)
    if len(parts) == 2:
        # Build a statistics function
        func_name, field_name = parts
        func = _reducer(aggregators[func_name], operator.itemgetter(field_name))
    elif len(parts) == 3:
        # Build a counting function
        field_name, op, value = parts
        func = _reducer(sum, _comparison_function(field_name, op, [value]))
    else:
        raise LivestatusTestingError(f"Unknown Stats line: {line}")

    return func


def evaluate_filter(query: str, result: ResultList) -> ResultList:
    """Filter a list of dictionaries according to the filters of a LiveStatus query.

    The filters will be extracted from the query. And: and Or: directives are also supported.

    Currently, only standard "Filter:" directives are supported, not StatsFilter: etc.

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

        >>> q = "GET hosts\\nFilter: name = heute\\nFilter: state > 0"
        >>> evaluate_filter(q, data)
        []

        >>> q = "GET hosts\\nFilter: name = heute\\nFilter: state > 0\\nAnd: 2"
        >>> evaluate_filter(q, data)
        []

        >>> q = "GET hosts\\nFilter: name = heute\\nFilter: state = 0"
        >>> evaluate_filter(q, data)
        [{'name': 'heute', 'state': 0}]

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
    for line in query.splitlines():
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

    # Implicit "And", as this is supported by Livestatus.
    if len(filters) > 1:
        filters = [and_(filters)]

    assert len(filters) == 1
    return [entry for entry in result if filters[0](entry)]


def and_(filters: List[FilterKeyFunc]) -> FilterKeyFunc:
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
        return all(filt(entry) for filt in filters)

    return _and_impl


def or_(filters: List[FilterKeyFunc]) -> FilterKeyFunc:
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
        return any(filt(entry) for filt in filters)

    return _or_impl


COMBINATORS: Dict[str, Callable[[List[FilterKeyFunc]], FilterKeyFunc]] = {
    "And:": and_,
    "Or:": or_,
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
    "=": cast_down(operator.eq),
    ">": cast_down(operator.gt),
    "<": cast_down(operator.lt),
    ">=": cast_down(operator.ge),
    "<=": cast_down(operator.le),
    "~": match_regexp,
}
"""A dict of all implemented comparison operators."""


def make_filter_func(line: str) -> FilterKeyFunc:
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

        Ints work as well:

            >>> f = make_filter_func("Filter: state = 0")
            >>> f({'state': 0})
            True

            >>> f({'state': 1})
            False

        If not implemented, yell:

            >>> f = make_filter_func("Filter: name !! heute")
            Traceback (most recent call last):
            ...
            livestatus.LivestatusTestingError: Operator '!!' not implemented. Please check docs or implement.


    """
    field_name, op, *value = line[7:].split(None, 2)  # strip Filter: as len("Filter:") == 7
    if op not in OPERATORS:
        raise LivestatusTestingError(
            f"Operator {op!r} not implemented. Please check docs or implement."
        )

    # For checking empty values. In this case an empty list.
    if not value:
        value = [""]

    return _comparison_function(field_name, op, value)


def _comparison_function(field_name: str, op: Operator, value: List[Any]) -> FilterKeyFunc:
    """Create a comparison function

    Examples:

        >>> _comparison_function("foo", "=", ["1"])({'foo': 1})
        True

        >>> _comparison_function("foo", ">", ["1"])({'foo': 1})
        False

        >>> _comparison_function("foo", ">", ["1"])({})
        Traceback (most recent call last):
        ...
        KeyError: 'foo'

    Args:
        field_name:
            The field, to which the value shall be compared

        op:
            The operator with which to compare

        value:
            The value to compare against

    Returns:
        A function which take a dictionary and returns a boolean.

    """

    def _apply_op(entry: ResultEntry) -> bool:
        return OPERATORS[op](entry[field_name], *value)

    return _apply_op


def _column_of_query(query: str) -> Optional[List[ColumnName]]:
    """Figure out the queried columns from a LiveStatus query.

    Args:
        query:
            A LiveStatus query as a string.

    Returns:
        A list of column names referenced by the query. This may also include generated columns
        by Stats headers.

    Examples:

        >>> _column_of_query('GET hosts\\nColumns: name status alias\\nFilter: name = foo')
        ['name', 'status', 'alias']

        >>> _column_of_query('GET hosts\\nFilter: name = foo')

    """
    for line in query.splitlines():
        if line.startswith("Columns:"):
            return line[8:].split()  # len("Columns:") == 8

    return None


def _table_of_query(query: str) -> Optional[TableName]:
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
    lines = query.splitlines()
    if lines and lines[0].startswith("GET "):
        return lines[0].split(None, 1)[1]

    return None


def _unpack_headers(query: str) -> Dict[str, str]:
    r"""Unpack and normalize headers from a string.

    Examples:

        >>> _unpack_headers("GET hosts\nColumnHeaders: off")
        {'ColumnHeaders': 'off'}

        >>> _unpack_headers("ColumnHeaders: off\nResponseFormat: fixed16")
        {'ColumnHeaders': 'off', 'ResponseFormat': 'fixed16'}

        >>> _unpack_headers("Foobar!")
        {}

    Args:
        query:
            Query as a string.

    Returns:
        Headers of query as a dict.

    """
    unpacked = {}
    for header in query.splitlines():
        if header.startswith("GET "):
            continue
        if ": " not in header:
            continue
        if not header:
            continue
        key, value = header.split(": ", 1)
        unpacked[key] = value.lstrip(" ")
    return unpacked

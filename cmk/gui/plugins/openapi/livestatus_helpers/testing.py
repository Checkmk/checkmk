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
import re
import time
from typing import Any, List, Literal, Optional, Union

# TODO: Make livestatus.py a well tested package on pypi
# TODO: Move this code to the livestatus package
# TODO: Multi-site support. Need to have multiple lists of queries, one per site.

MatchType = Literal["strict", "ellipsis"]
Response = List[List[Any]]


class MockLiveStatusConnection:
    """Mock a LiveStatus connection.

    NOTE:
        You probably want to use the fixture: cmk.gui.conftest:mock_livestatus

    This object can remember queries and the order in which they should arrive. Once the expected
    query was accepted, the pre-stored response will be given back.

    It is up to the test-writer to set the appropriate queries and their responses.

    The class will verify that:
     * The expected queries (and _only_ those) are being issued in the `with` block.
       This means that:
         * Any additional query will trigger a RuntimeError
         * Any missing query will trigger a RuntimeError
         * Any mismatched query will trigger a RuntimeError
         * Any wrong order of queries will trigger a RuntimeError

    Args:
        report_multiple (bool):
            When set to True, this will potentially trigger mutliple Exceptions on __exit__. This
            can be useful when debugging chains of queries. Default is False.

    Examples:

        This will pass:

            >>> live = (MockLiveStatusConnection()
            ...         .expect_query("GET hosts")
            ...         .expect_query("GET services"))
            >>> with live(expect_status_query=False):
            ...     live.query_non_parallel("GET hosts", '')
            ...     live.query_non_parallel("GET services", '')

        This will pass as well (useful in real WATO or REST-API calls):

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
    def __init__(self, report_multiple=False):
        self._prepend_site = False
        self._expected_queries = []
        self._num_queries = 0
        self._query_index = 0
        self._report_multiple = report_multiple
        self._expect_status_query = None

    def _expect_post_connect_query(self) -> None:
        # cmk.gui.sites._connect_multiple_sites asks for the some specifics upon initial connection.
        # We expect this query and give the expected result.
        today = str(dt.date.today())
        program_start_timestamp = int(time.time())
        self.expect_query(
            [
                'GET status',
                'Cache: reload',
                'Columns: livestatus_version program_version program_start num_hosts num_services',
            ],
            result=[[today, 'Check_MK ' + today, program_start_timestamp, 1, 36]],
            force_pos=0,  # first query to be expected
        )

    def __call__(self, expect_status_query=True) -> 'MockLiveStatusConnection':
        self._expect_status_query = expect_status_query
        return self

    def __enter__(self):
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
            raise RuntimeError(f"Expected queries were not queried:" f"{remaining_queries}")

    def expect_query(
        self,
        query: Union[str, List[str]],
        result: List[List[Any]] = None,
        match_type: MatchType = 'strict',
        force_pos: Optional[int] = None,
    ) -> 'MockLiveStatusConnection':
        """Add a LiveStatus query to be expected by this class.

        This method is chainable, as it returns the instance again.

        Args:
            query:
                The expected query. May be a `str` or a list of `str` which will tehn be joined by
                newlines.

            result:
                What the result of this query should be.

            match_type:
                Flags with which to decide comparison behavior.
                Can be either 'strict' or 'ellipsis'. In case of 'ellipsis', the supplied query
                can have placeholders in the form of '...'. These placeholders are ignored in the
                comparison.

            force_pos:
                Only used internally. Ignore.
        """
        if match_type not in ('strict', 'ellipsis'):
            raise ValueError(f"match_type {match_type!r} not supported.")

        if isinstance(query, list):
            query = '\n'.join(query)

        if force_pos is not None:
            self._expected_queries.insert(force_pos, (query, result, match_type))
        else:
            self._expected_queries.append((query, result, match_type))

        return self

    def _lookup_next_query(self, query, headers) -> Response:
        if self._expect_status_query is None:
            raise RuntimeError("Please use MockLiveStatusConnection as a context manager.")

        if headers:
            raise RuntimeError("Extra headers checking not yet implemented.")

        # We don't want to str() cmk.gui.plugins.openapi.livestatus_helpers.queries.Query because
        # livestatus.py doesn't support it yet. We want it to crash if we ever get one here.
        if hasattr(query, 'default_suppressed_exceptions'):
            query = str(query)

        if not self._expected_queries:
            raise RuntimeError(f"Got unexpected query:\n" f" * {repr(query)}")

        expected_query, response, match_type = self._expected_queries[0]

        if not _compare(expected_query, query, match_type):
            raise RuntimeError(f"Expected query:\n"
                               f" * {repr(expected_query)}\n"
                               f"Got query:\n"
                               f" * {repr(query)}")

        # Passed, remove this entry.
        self._expected_queries.pop(0)

        if self._prepend_site:
            return [['NO_SITE'] + line for line in response]

        return response

    # Mocked livestatus api below
    def get_connection(self, site_id: str) -> 'MockLiveStatusConnection':
        return self

    def command(self, command: str, site: Optional[str] = 'local') -> None:
        self.do_command(command)

    def do_command(self, command: str) -> None:
        self._lookup_next_query(f"COMMAND {command}", [])

    def set_prepend_site(self, prepend_site: bool) -> None:
        self._prepend_site = prepend_site

    def query_parallel(self, query, headers) -> Response:
        return self._lookup_next_query(query, headers)

    def query_non_parallel(self, query, headers) -> Response:
        return self._lookup_next_query(query, headers)


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
def simple_expect(query, match_type: MatchType = "ellipsis", expect_status_query=False):
    """A simplified testing context manager."""
    live = MockLiveStatusConnection()
    live.expect_query(query, match_type=match_type)
    with live(expect_status_query=expect_status_query):
        yield live

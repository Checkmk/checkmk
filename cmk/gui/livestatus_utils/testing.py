#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import os
from typing import Iterator
from unittest import mock

from livestatus import MultiSiteConnection

from cmk.utils.livestatus_helpers.testing import MatchType, MockLiveStatusConnection
from cmk.utils.site import omd_site

from cmk.gui import sites
from cmk.gui.utils.script_helpers import application_and_request_context


@contextlib.contextmanager
def mock_livestatus() -> Iterator[MockLiveStatusConnection]:
    live = MockLiveStatusConnection()
    with mock.patch(
        "cmk.gui.sites._get_enabled_and_disabled_sites", new=live.enabled_and_disabled_sites
    ), mock.patch(
        "livestatus.MultiSiteConnection.expect_query", new=live.expect_query, create=True
    ), mock.patch(
        "livestatus.SingleSiteConnection._create_socket", new=live.create_socket
    ):
        yield live


@contextlib.contextmanager
def mock_site() -> Iterator[None]:
    with mock.patch.dict(os.environ, {"OMD_ROOT": "/", "OMD_SITE": "NO_SITE"}):
        # We don't want to be polluted by other tests.
        omd_site.cache_clear()
        try:
            yield
        finally:
            # We don't want to pollute other tests.
            omd_site.cache_clear()


# This function is used extensively in doctests. If we moved the tests to regular pytest tests, we
# could make use of existing fixtures and simplify all this. When looking at the doctests in
# cmk/utils/livestatus_helpers/queries.py it looks like many of then should better be unit tests.
@contextlib.contextmanager
def simple_expect(
    query: str = "",
    match_type: MatchType = "loose",
    expect_status_query: bool = True,
) -> Iterator[MultiSiteConnection]:
    """A simplified testing context manager.

    Args:
        query:
            A livestatus query.

        match_type:
            Either 'strict', 'loose' or 'ellipsis'. Default is 'loose'.

        expect_status_query:
            If the query of the status table (which Checkmk does when calling sites.live()) should
            be expected. Defaults to False.

    Returns:
        A context manager.

    Examples:

        >>> with simple_expect("GET hosts") as _live:
        ...    _ = _live.query("GET hosts")

    """
    with application_and_request_context(), mock_site(), mock_livestatus() as mock_live:
        if query:
            mock_live.expect_query(query, match_type=match_type)
        with mock_live(expect_status_query=expect_status_query):
            yield sites.live()

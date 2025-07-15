#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import os
from collections.abc import Iterator
from unittest import mock

from livestatus import MultiSiteConnection

from cmk.ccc.site import omd_site

from cmk.utils.livestatus_helpers.testing import (
    MatchType,
    mock_livestatus_communication,
    MockLiveStatusConnection,
)

from cmk.gui import sites
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import application_and_request_context


@contextlib.contextmanager
def mock_livestatus() -> Iterator[MockLiveStatusConnection]:
    with (
        mock_livestatus_communication() as mock_live,
        mock.patch(
            "cmk.gui.sites._get_enabled_and_disabled_sites",
            new=mock_live.enabled_and_disabled_sites,
        ),
    ):
        yield mock_live


@contextlib.contextmanager
def mock_site() -> Iterator[None]:
    env_vars = {"OMD_ROOT": "/", "OMD_SITE": os.environ.get("OMD_SITE", "NO_SITE")}
    with mock.patch.dict(os.environ, env_vars):
        # We don't want to be polluted by other tests.
        omd_site.cache_clear()
        try:
            yield
        finally:
            # We don't want to pollute other tests.
            omd_site.cache_clear()


# This function is used extensively in doctests. If we moved the tests to regular pytest tests, we
# could make use of existing fixtures and simplify all this. When looking at the doctests in
# cmk/gui/livestatus_utils/commands/*.py it looks like many of then should better be unit tests.
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
    with (
        mock_site(),
        application_and_request_context(),
        mock_livestatus() as mock_live,
        SuperUserContext(),
    ):
        if query:
            mock_live.expect_query(query, match_type=match_type)
        with mock_live(expect_status_query=expect_status_query):
            yield sites.live()

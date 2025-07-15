#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.site import SiteId

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.gui.wato._ac_tests import _compute_deprecation_result, ACTestGenericCheckHelperUsage
from cmk.gui.watolib.analyze_configuration import ACResultState, ACSingleResult


def test_local_connection_mocked(
    mock_livestatus: MockLiveStatusConnection, request_context: None
) -> None:
    live = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.expect_query(
        [
            "GET status",
            "Columns: helper_usage_generic average_latency_generic",
            "ColumnHeaders: off",
        ]
    )
    with live(expect_status_query=False):
        gen = ACTestGenericCheckHelperUsage().execute()
        list(gen)


@pytest.mark.parametrize(
    "version, result",
    [
        pytest.param(
            "1.2.6",
            ACSingleResult(
                state=ACResultState.CRIT,
                text="Entity uses an API (API) which was removed in Checkmk 1.2.5 (File: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="was_removed",
        ),
        pytest.param(
            "1.2.5",
            ACSingleResult(
                state=ACResultState.CRIT,
                text="Entity uses an API (API) which was marked as deprecated in Checkmk 1.2.3 and is removed in Checkmk 1.2.5 (File: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="removed",
        ),
        pytest.param(
            "1.2.4",
            ACSingleResult(
                state=ACResultState.WARN,
                text="Entity uses an API (API) which was marked as deprecated in Checkmk 1.2.3 and will be removed in Checkmk 1.2.5 (File: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="was_deprecated",
        ),
        pytest.param(
            "1.2.3",
            ACSingleResult(
                state=ACResultState.WARN,
                text="Entity uses an API (API) which is marked as deprecated in Checkmk 1.2.3 and will be removed in Checkmk 1.2.5 (File: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="deprecated",
        ),
        pytest.param(
            "1.2.2",
            ACSingleResult(
                state=ACResultState.OK,
                text="",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="ok",
        ),
    ],
)
def test__compute_deprecation_result(version: str, result: ACSingleResult) -> None:
    assert (
        _compute_deprecation_result(
            version=version,
            deprecated_version="1.2.3",
            removed_version="1.2.5",
            title_entity="Entity",
            title_api="API",
            site_id=SiteId("site_id"),
            path=Path("/path/to/file"),
        )
        == result
    )

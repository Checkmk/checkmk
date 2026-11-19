#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.ccc.site import SiteId
from cmk.gui import sites, user_sites
from cmk.livestatus_client import (
    SiteConfiguration,
    SiteConfigurations,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection


@pytest.mark.usefixtures("request_context")
def test_sorted_sites() -> None:
    expected = [
        ("site1", "Site 1"),
        ("site12", "Site 12"),
        ("site23", "Site 23"),
        ("site3", "Site 3"),
        ("site5", "Site 5"),
        ("site6", "Site 6"),
    ]
    assert (
        user_sites.sorted_sites(
            SiteConfigurations(
                {
                    SiteId("site1"): _site_config(SiteId("site1"), "Site 1"),
                    SiteId("site3"): _site_config(SiteId("site3"), "Site 3"),
                    SiteId("site5"): _site_config(SiteId("site5"), "Site 5"),
                    SiteId("site6"): _site_config(SiteId("site6"), "Site 6"),
                    SiteId("site12"): _site_config(SiteId("site12"), "Site 12"),
                    SiteId("site23"): _site_config(SiteId("site23"), "Site 23"),
                }
            )
        )
        == expected
    )


@pytest.mark.usefixtures("load_config")
def test_only_sites_restores_the_enclosing_restriction(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(), sites.only_sites(SiteId("local")):
        with sites.only_sites(SiteId("remote")):
            pass

        assert sites.live().only_sites == [SiteId("local")]


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize(
    "only_sites, expected",
    [
        pytest.param(None, [SiteId("local"), SiteId("remote")], id="no filter"),
        pytest.param([], [SiteId("local"), SiteId("remote")], id="empty filter"),
        pytest.param([SiteId("remote")], [SiteId("remote")], id="dead site requested"),
        pytest.param([SiteId("NO_SITE")], [], id="dead site not requested"),
    ],
)
def test_unreachable_sites_names_dead_sites_among_the_requested_ones(
    mock_livestatus: MockLiveStatusConnection,
    only_sites: list[SiteId] | None,
    expected: list[SiteId],
) -> None:
    mock_livestatus.make_site_unreachable("remote")
    mock_livestatus.make_site_unreachable("local")

    with mock_livestatus():
        assert sites.unreachable_sites(only_sites) == expected


def _site_config(site_id: SiteId, alias: str) -> SiteConfiguration:
    return SiteConfiguration(
        id=site_id,
        alias=alias,
        socket=("local", None),
        disable_wato=True,
        disabled=False,
        insecure=False,
        url_prefix="/mysite/",
        multisiteurl="",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave",
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )

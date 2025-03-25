#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pytest_mock.plugin import MockerFixture

from livestatus import SiteId

import cmk.utils.paths

from cmk.gui import sites, user_sites
from cmk.gui.logged_in import user

from cmk.livestatus_client import NetworkSocketDetails, UnixSocketDetails


def test_encode_socket_for_livestatus_local() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"), {"socket": ("local", None), "proxy": None}
        )
        == f"unix:{cmk.utils.paths.omd_root}/tmp/run/live"
    )


def test_encode_socket_for_livestatus_local_liveproxy() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"), {"socket": ("local", None), "proxy": {"params": None}}
        )
        == f"unix:{cmk.utils.paths.omd_root}/tmp/run/liveproxy/mysite"
    )


def test_encode_socket_for_livestatus_unix() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"),
            {"socket": ("unix", UnixSocketDetails(path="/a/b/c")), "proxy": None},
        )
        == "unix:/a/b/c"
    )


def test_encode_socket_for_livestatus_unix_liveproxy() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"),
            {"socket": ("unix", UnixSocketDetails(path="/a/b/c")), "proxy": {"params": None}},
        )
        == f"unix:{cmk.utils.paths.omd_root}/tmp/run/liveproxy/mysite"
    )


def test_encode_socket_for_livestatus_tcp() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"),
            {
                "socket": (
                    "tcp",
                    NetworkSocketDetails(address=("127.0.0.1", 1234), tls=("plain_text", {})),
                ),
                "proxy": None,
            },
        )
        == "tcp:127.0.0.1:1234"
    )


def test_encode_socket_for_livestatus_tcp6() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"),
            {
                "socket": (
                    "tcp6",
                    NetworkSocketDetails(address=("::1", 1234), tls=("plain_text", {})),
                ),
                "proxy": None,
            },
        )
        == "tcp6:::1:1234"
    )


def test_site_config_for_livestatus_tcp_tls() -> None:
    assert sites._site_config_for_livestatus(
        SiteId("mysite"),
        {
            "socket": (
                "tcp",
                NetworkSocketDetails(
                    address=("127.0.0.1", 1234), tls=("encrypted", {"verify": True})
                ),
            ),
            "proxy": None,
        },
    ) == {
        "socket": "tcp:127.0.0.1:1234",
        "tls": ("encrypted", {"verify": True}),
        "proxy": None,
    }


def test_sorted_sites(mocker: MockerFixture, request_context: None) -> None:
    mocker.patch.object(
        user,
        "authorized_sites",
        return_value={
            "site1": {"alias": "Site 1"},
            "site3": {"alias": "Site 3"},
            "site5": {"alias": "Site 5"},
            "site23": {"alias": "Site 23"},
            "site6": {"alias": "Site 6"},
            "site12": {"alias": "Site 12"},
        },
    )
    expected = [
        ("site1", "Site 1"),
        ("site12", "Site 12"),
        ("site23", "Site 23"),
        ("site3", "Site 3"),
        ("site5", "Site 5"),
        ("site6", "Site 6"),
    ]
    assert user_sites.sorted_sites() == expected
    mocker.stopall()

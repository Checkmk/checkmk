#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.site import SiteId
from cmk.livestatus_client import (
    encode_socket_for_livestatus,
    NetworkSocketDetails,
    site_config_for_livestatus,
    SiteConfiguration,
    UnixSocketDetails,
)

LOCAL_SOCKET = Path("/omd/sites/mysite/tmp/run/live")


def default_site_config() -> SiteConfiguration:
    return SiteConfiguration(
        id=SiteId("mysite"),
        alias="Local site mysite",
        socket=("local", None),
        disable_wato=True,
        disabled=False,
        insecure=False,
        url_prefix="/mysite/",
        multisiteurl="",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication=None,
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )


def test_encode_socket_for_livestatus_local() -> None:
    assert (
        encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config() | {"socket": ("local", None), "proxy": None},
            LOCAL_SOCKET,
        )
        == "unix:/omd/sites/mysite/tmp/run/live"
    )


def test_encode_socket_for_livestatus_local_liveproxy() -> None:
    assert (
        encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config() | {"socket": ("local", None), "proxy": {"params": None}},
            LOCAL_SOCKET,
        )
        == "unix:/omd/sites/mysite/tmp/run/liveproxy/mysite"
    )


def test_encode_socket_for_livestatus_unix() -> None:
    assert (
        encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config()
            | {"socket": ("unix", UnixSocketDetails(path="/a/b/c")), "proxy": None},
            LOCAL_SOCKET,
        )
        == "unix:/a/b/c"
    )


def test_encode_socket_for_livestatus_unix_liveproxy() -> None:
    assert (
        encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config()
            | {"socket": ("unix", UnixSocketDetails(path="/a/b/c")), "proxy": {"params": None}},
            LOCAL_SOCKET,
        )
        == "unix:/omd/sites/mysite/tmp/run/liveproxy/mysite"
    )


def test_encode_socket_for_livestatus_tcp() -> None:
    assert (
        encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config()
            | {
                "socket": (
                    "tcp",
                    NetworkSocketDetails(address=("127.0.0.1", 1234), tls=("plain_text", {})),
                ),
                "proxy": None,
            },
            LOCAL_SOCKET,
        )
        == "tcp:127.0.0.1:1234"
    )


def test_encode_socket_for_livestatus_tcp6() -> None:
    assert (
        encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config()
            | {
                "socket": (
                    "tcp6",
                    NetworkSocketDetails(address=("::1", 1234), tls=("plain_text", {})),
                ),
                "proxy": None,
            },
            LOCAL_SOCKET,
        )
        == "tcp6:::1:1234"
    )


def test_site_config_for_livestatus_tcp_tls() -> None:
    site_config = site_config_for_livestatus(
        SiteId("mysite"),
        default_site_config()
        | {
            "socket": (
                "tcp",
                NetworkSocketDetails(
                    address=("127.0.0.1", 1234), tls=("encrypted", {"verify": True})
                ),
            ),
            "proxy": None,
        },
        LOCAL_SOCKET,
    )
    assert site_config["socket"] == "tcp:127.0.0.1:1234"
    assert site_config["tls"] == ("encrypted", {"verify": True})
    assert site_config["proxy"] is None

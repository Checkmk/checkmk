#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# my py: disable-error-code="misc"
# my py: disable-error-code="type-arg"


import datetime
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.forwarder import ForwardedResult, MessageForwarder


class FakeTcpError(Exception):
    pass


class FakeTcpErrorRaised(Exception):
    pass


def _forward_message(
    tcp_result: Literal["ok", "raise exception", "set exception"],
    spool_path: Path = Path("/dev/null"),
    method: tuple[str, dict[str, object]] = ("tcp", {"address": "127.0.0.1", "port": 127001}),
    text: str = "some_text",
    item: str | None = None,
    application: str = "-",
    timestamp: str = "2023-11-11 11:11:00Z",
) -> tuple[ForwardedResult, list[tuple[float, int, list[str]]]]:
    messages_forwarded: list[tuple[float, int, list[str]]] = []

    class TestForwardTcpMessageForwarder(MessageForwarder):
        @staticmethod
        def _forward_send_tcp(
            _method: object,
            message_chunks: Iterable[tuple[float, int, list[str]]],
            result: ForwardedResult,
        ) -> None:
            nonlocal messages_forwarded
            if tcp_result == "ok":
                for message in message_chunks:
                    messages_forwarded.append(message)
                    result.num_forwarded += 1
            elif tcp_result == "set exception":
                result.exception = FakeTcpError("could not send messages")
            elif tcp_result == "raise exception":
                raise FakeTcpErrorRaised("rise and shine")
            else:
                raise NotImplementedError()

    result = TestForwardTcpMessageForwarder(
        item=item,
        hostname=HostName("some_host_name"),
        base_spool_path=spool_path,
        omd_root=Path("/dev/null"),
        debug=False,
    )(
        method=method,
        messages=[
            ec.SyslogMessage(
                facility=1, severity=1, timestamp=0.0, text=text, application=application
            )
        ],
        timestamp=datetime.datetime.fromisoformat(timestamp).timestamp(),
    )

    return result, messages_forwarded


def test_forward_tcp_message_forwarded_ok() -> None:
    result, messages_forwarded = _forward_message(tcp_result="ok")
    assert result == ForwardedResult(
        num_forwarded=1,
        num_spooled=0,
        num_dropped=0,
        exception=None,
    )

    assert len(messages_forwarded) == 1
    # first element of message is a timestamp!
    assert messages_forwarded[0][1:] == (
        0,
        ["<9>1 1970-01-01T00:00:00+00:00 - - - - [Checkmk@18662] some_text"],
    )


def test_forward_tcp_message_forwarded_nok_1() -> None:
    result, messages_forwarded = _forward_message(tcp_result="set exception")

    assert result.num_forwarded == 0
    assert result.num_spooled == 0
    assert result.num_dropped == 1
    assert isinstance(result.exception, FakeTcpError)

    assert len(messages_forwarded) == 0


def test_forward_tcp_message_forwarded_nok_2() -> None:
    result, messages_forwarded = _forward_message(tcp_result="raise exception")

    assert result.num_forwarded == 0
    assert result.num_spooled == 0
    assert result.num_dropped == 1
    assert isinstance(result.exception, FakeTcpErrorRaised)

    assert len(messages_forwarded) == 0


SPOOL_METHOD = (
    "tcp",
    {
        "address": "127.0.0.1",
        "port": 127001,
        "spool": {"max_age": 60 * 60, "max_size": 1024 * 1024},
    },
)


def test_forward_tcp_message_forwarded_spool(tmp_path: Path) -> None:
    spool_dir = tmp_path / "logwatch_spool"
    # could not send message, so spool it
    result, messages_forwarded = _forward_message(
        tcp_result="set exception",
        spool_path=spool_dir,
        method=SPOOL_METHOD,
        text="spooled",
    )
    assert result.num_forwarded == 0
    assert result.num_spooled == 1
    assert result.num_dropped == 0
    assert isinstance(result.exception, FakeTcpError)
    assert len(messages_forwarded) == 0

    # sending works again, so send both of them
    result, messages_forwarded = _forward_message(
        tcp_result="ok",
        spool_path=spool_dir,
        method=SPOOL_METHOD,
        text="directly_sent_1",
    )
    assert result.num_forwarded == 2
    assert result.num_spooled == 0
    assert result.num_dropped == 0
    assert len(messages_forwarded) == 2

    assert messages_forwarded[0][2][0].rsplit(" ", 1)[-1] == "spooled"
    assert messages_forwarded[1][2][0].rsplit(" ", 1)[-1] == "directly_sent_1"

    # sending is still working, so send only one
    result, messages_forwarded = _forward_message(
        tcp_result="ok",
        spool_path=spool_dir,
        method=SPOOL_METHOD,
        text="directly_sent_2",
    )
    assert result.num_forwarded == 1
    assert result.num_spooled == 0
    assert result.num_dropped == 0
    assert len(messages_forwarded) == 1

    assert messages_forwarded[0][2][0].rsplit(" ", 1)[-1] == "directly_sent_2"


def test_forward_tcp_message_forwarded_spool_twice(tmp_path: Path) -> None:
    # we delete the original spool file after reading it.
    # here we want to make sure, that the spool file is recreated. otherwise messages from different
    # time would land into the same spool file and may not be correctly cleaned up.
    spool_dir = tmp_path / "logwatch_spool/some_host_name"

    # create a spooled message:
    result, messages_forwarded = _forward_message(
        tcp_result="set exception",
        spool_path=spool_dir.parent,
        method=SPOOL_METHOD,
        timestamp="2023-10-31 16:02:00Z",
    )
    assert result.num_forwarded == 0
    assert result.num_spooled == 1
    assert result.num_dropped == 0
    assert isinstance(result.exception, FakeTcpError)
    assert len(messages_forwarded) == 0

    # we expect one spool file to be created:
    assert [f.name for f in spool_dir.iterdir()] == ["spool.1698768120.00"]

    # create another spooled message:
    result, messages_forwarded = _forward_message(
        tcp_result="set exception",
        spool_path=spool_dir.parent,
        method=SPOOL_METHOD,
        timestamp="2023-10-31 16:03:00Z",
    )
    assert result.num_forwarded == 0
    assert result.num_spooled == 2
    assert result.num_dropped == 0
    assert isinstance(result.exception, FakeTcpError)
    assert len(messages_forwarded) == 0

    # now let's see if we have two spool files
    assert {f.name for f in spool_dir.iterdir()} == {
        "spool.1698768120.00",
        "spool.1698768180.00",
    }


def test_logwatch_spool_path_is_escaped() -> None:
    # item may contain slashes or other stuff, we want to make sure
    # that this is transformed to a single folder name:
    get_spool_path = MessageForwarder(  # noqa: SLF001
        item="some/log/path",
        hostname=HostName("some_host_name"),
        base_spool_path=Path("/dev/null"),
        omd_root=Path("/dev/null"),
        debug=False,
    )._get_spool_path
    result = get_spool_path(HostName("some_host_name"), "some/log/path")
    assert result.name == "item_some%2Flog%2Fpath"
    assert result.parent.name == "some_host_name"

    assert get_spool_path(HostName("short"), ".").name == "item_."
    assert get_spool_path(HostName("short"), "..").name == "item_.."

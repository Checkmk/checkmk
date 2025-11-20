#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.emailchecks.lib.connections import (
    EmailAddress,
    GraphApiMessage,
    Recipient,
    verified_result,
)


@pytest.mark.parametrize(
    ["data", "result"],
    [
        # IMAP
        (
            ("OK", [b"wwwwwwwwwwwwww@gmail.com authenticated (Success)"]),
            [b"wwwwwwwwwwwwww@gmail.com authenticated (Success)"],
        ),
        (
            ("OK", [(b"1 (RFC822 {14630}", b"lots", b"data", b")")]),
            [(b"1 (RFC822 {14630}", b"lots", b"data", b")")],
        ),
        (("OK", ["payload"]), ["payload"]),
        # POP
        ((b"+OK message follows", [b"some payload"]), [b"some payload"]),
        # server returned an error
        (("NO", []), RuntimeError),
        ((b"NO", []), RuntimeError),
        # not expected data
        ((None,), AssertionError),
        # POP without payload
        (b"+OK 1 236", []),
        # POP without payload and error
        (b"-ERR no such message", RuntimeError),
        # probably just for making mypy happy
        (None, TypeError),
        # not sure if this really can happen
        (("OK", []), []),
        (("OK", [None]), TypeError),
        (("OK", ["a", b"b"]), TypeError),
    ],
)
def test_verified_result(
    data: object,
    result: list[str | bytes] | type[TypeError] | type[RuntimeError] | type[AssertionError],
) -> None:
    if isinstance(result, list):
        assert result == verified_result(data)
    else:
        with pytest.raises(result):
            verified_result(data)


@pytest.mark.parametrize(
    ["data", "expected"],
    [
        (
            {
                "id": "message-id-123",
                "subject": "Test Subject",
                "from": {"emailAddress": {"address": "foo.bar@barmail.tv"}},
            },
            GraphApiMessage(
                id="message-id-123",
                subject="Test Subject",
                from_=Recipient(emailAddress=EmailAddress(address="foo.bar@barmail.tv")),
            ),
        ),
        (
            {
                "id": "message-id-124",
                "subject": "Test Subject 2",
                "from": {"emailAddress": {"address": "bar.foo@barmail.tv"}},
                "extra_field": "should be ignored",
                "another_one": 12345,
            },
            GraphApiMessage(
                id="message-id-124",
                subject="Test Subject 2",
                from_=Recipient(emailAddress=EmailAddress(address="bar.foo@barmail.tv")),
            ),
        ),
    ],
)
def test_graph_api_message_deserialization(
    data: dict[str, object],
    expected: GraphApiMessage,
) -> None:
    msg = GraphApiMessage.model_validate(data)
    assert msg == expected


@pytest.mark.parametrize(
    ["data", "expected"],
    [
        (
            GraphApiMessage(
                id="message-id-123",
                subject="Test Subject",
                from_=Recipient(emailAddress=EmailAddress(address="foo.bar@barmail.tv")),
            ),
            {
                "id": "message-id-123",
                "subject": "Test Subject",
                "body": {},
                "from": {"emailAddress": {"address": "foo.bar@barmail.tv"}},
                "toRecipients": [],
                "receivedDateTime": None,
            },
        ),
    ],
)
def test_graph_api_message_serialization(
    data: GraphApiMessage,
    expected: dict[str, object],
) -> None:
    msg = GraphApiMessage.model_dump(data, by_alias=True)
    assert msg == expected

#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.plugins.emailchecks.lib.connections import verified_result


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
        # POP (2-element tuple)
        ((b"+OK message follows", [b"some payload"]), [b"some payload"]),
        # POP (3-element tuple, as returned by poplib list/retr)
        ((b"+OK 2 messages:", [b"1 3035", b"2 38374"], 17), [b"1 3035", b"2 38374"]),
        ((b"+OK message follows", [b"line1", b"line2"], 42), [b"line1", b"line2"]),
        # POP 3-element tuple with error
        ((b"-ERR no such message", [], 0), RuntimeError),
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

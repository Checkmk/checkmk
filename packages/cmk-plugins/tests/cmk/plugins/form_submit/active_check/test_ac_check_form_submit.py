#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import email.message
import io
import os
import urllib.request
import urllib.response
from collections.abc import Mapping, Sequence

import pytest
import vcr  # type: ignore[import-untyped,unused-ignore]

from cmk.plugins.form_submit.active_check import check_form_submit


@pytest.mark.parametrize(
    "args, expected_exitcode, expected_info",
    [
        (
            [
                "localhost",
                "--uri",
                "/heute",
            ],
            0,
            "Form has been submitted",
        ),
        (
            [
                "localhost",
                "--uri",
                "/heute",
                "--query",
                '"_origtarget=wato.py&_username=cmkadmin&_password=cmk"',
                "--expected_regex",
                "wato",
            ],
            0,
            'Found expected regex "wato" in form response',
        ),
        (
            [
                "localhost",
                "--uri",
                "/heute",
                "--query",
                '"_origtarget=wato.py&_username=cmkadmin&_password=cmk"',
                "--expected_regex",
                "lala",
            ],
            2,
            'Expected regex "lala" could not be found in form response',
        ),
    ],
)
def test_check_form_submit_main(
    args: Sequence[str],
    expected_exitcode: int,
    expected_info: str,
) -> None:
    filepath = "%s/_check_form_submit_response" % os.path.dirname(__file__)
    with vcr.use_cassette(  # type: ignore[no-untyped-call,unused-ignore]
        filepath,
        record_mode="none",
    ):
        exitcode, info = check_form_submit.main(args)
        assert exitcode == expected_exitcode
        assert info == expected_info


@pytest.mark.parametrize(
    "states, expected_status, expected_info",
    [
        ({}, 0, "0 succeeded, 0 failed"),
        ({"foo": (0, "SOME_TEXT")}, 0, "1 succeeded, 0 failed"),
        ({"foo": (1, "SOME_TEXT")}, 1, "0 succeeded, 1 failed (foo: SOME_TEXT)"),
        ({"foo": (2, "SOME_TEXT")}, 2, "0 succeeded, 1 failed (foo: SOME_TEXT)"),
        ({"foo": (0, "SOME_TEXT_1"), "bar": (0, "SOME_TEXT_2")}, 0, "2 succeeded, 0 failed"),
        (
            {"foo": (1, "SOME_TEXT_1"), "bar": (0, "SOME_TEXT_2")},
            1,
            "1 succeeded, 1 failed (foo: SOME_TEXT_1)",
        ),
        (
            {"foo": (1, "SOME_TEXT_1"), "bar": (1, "SOME_TEXT_2")},
            1,
            "0 succeeded, 2 failed (bar: SOME_TEXT_2, foo: SOME_TEXT_1)",
        ),
        (
            {"foo": (2, "SOME_TEXT_1"), "bar": (0, "SOME_TEXT_2")},
            2,
            "1 succeeded, 1 failed (foo: SOME_TEXT_1)",
        ),
        (
            {"foo": (2, "SOME_TEXT_1"), "bar": (1, "SOME_TEXT_2")},
            2,
            "0 succeeded, 2 failed (bar: SOME_TEXT_2, foo: SOME_TEXT_1)",
        ),
        (
            {"foo": (2, "SOME_TEXT_1"), "bar": (2, "SOME_TEXT_2")},
            2,
            "0 succeeded, 2 failed (bar: SOME_TEXT_2, foo: SOME_TEXT_1)",
        ),
        (
            {"foo": (0, "SOME_TEXT_1"), "bar": (0, "SOME_TEXT_2"), "baz": (0, "SOME_TEXT_3")},
            0,
            "3 succeeded, 0 failed",
        ),
    ],
)
def test_ac_check_form_submit_host_states_no_levels(
    states: Mapping[str, tuple[int, str]],
    expected_status: int,
    expected_info: str,
) -> None:
    status, info = check_form_submit.check_host_states(states, None)
    assert status == expected_status
    assert info == expected_info


@pytest.mark.parametrize(
    "states, levels, expected_status, expected_info",
    [
        ({}, None, 0, "0 succeeded, 0 failed"),
        ({}, (0, 0), 2, "0 succeeded, 0 failed"),
        ({"foo": (0, "SOME_TEXT_1")}, None, 0, "1 succeeded, 0 failed"),
        ({"foo": (0, "SOME_TEXT_1")}, (0, 0), 0, "1 succeeded, 0 failed"),
        ({"foo": (0, "SOME_TEXT_1")}, (1, 1), 2, "1 succeeded, 0 failed"),
        ({"foo": (3, "SOME_TEXT_1")}, None, 3, "0 succeeded, 1 failed (foo: SOME_TEXT_1)"),
        ({"foo": (3, "SOME_TEXT_1")}, (0, 0), 2, "0 succeeded, 1 failed (foo: SOME_TEXT_1)"),
        ({"foo": (3, "SOME_TEXT_1")}, (1, 1), 2, "0 succeeded, 1 failed (foo: SOME_TEXT_1)"),
    ],
)
def test_ac_check_form_submit_host_states_levels(
    states: Mapping[str, tuple[int, str]],
    levels: tuple[int, int] | None,
    expected_status: int,
    expected_info: str,
) -> None:
    status, info = check_form_submit.check_host_states(states, levels)
    assert status == expected_status
    assert info == expected_info


def test_parse_form_reads_attribute_without_value_as_empty_string() -> None:
    form = check_form_submit.parse_form('<form method><input name="a" value></form>', None)
    assert form == check_form_submit.Form(attrs={"method": ""}, elements={"a": ""})


def test_parse_form_returns_single_form_with_matching_name() -> None:
    form = check_form_submit.parse_form('<form name="login"></form>', "login")
    assert form == check_form_submit.Form(attrs={"name": "login"}, elements={})


def test_parse_form_rejects_single_form_with_other_name() -> None:
    with pytest.raises(check_form_submit.HostResult) as excinfo:
        check_form_submit.parse_form('<form name="search"></form>', "login")
    assert excinfo.value.result == (
        2,
        'Found one form with name "search" but expected name "login"',
    )


class _FormPageHandler(urllib.request.BaseHandler):
    def __init__(self, page: str) -> None:
        self._page = page
        self.requested_urls: list[str] = []

    def http_open(self, request: urllib.request.Request) -> urllib.response.addinfourl:
        self.requested_urls.append(request.full_url)
        headers = email.message.Message()
        headers["Content-Type"] = "text/html; charset=utf-8"
        return urllib.response.addinfourl(
            io.BytesIO(self._page.encode()), headers, request.full_url, 200
        )


def _submit_form(form: str, uri: str) -> list[str]:
    handler = _FormPageHandler(form)
    client = urllib.request.OpenerDirector()
    client.add_handler(handler)

    with pytest.raises(check_form_submit.HostResult):
        check_form_submit.raise_host_state(
            client=client,
            base_url="http://host",
            args=argparse.Namespace(
                uri=uri, timeout=None, debug=False, form_name=None, expected_regex=None
            ),
            params={},
        )

    return handler.requested_urls


@pytest.mark.parametrize(
    "action, expected_target",
    [
        pytest.param("", "http://host/dir/page", id="empty"),
        pytest.param("submit", "http://host/dir/submit", id="relative path"),
        pytest.param("/submit", "http://host/submit", id="absolute path"),
        pytest.param("http://other/submit", "http://other/submit", id="absolute URL"),
    ],
)
def test_raise_host_state_submits_form_to_action(action: str, expected_target: str) -> None:
    assert _submit_form(
        f'<form method="post" action="{action}"><input name="a" value="1"></form>',
        "/dir/page",
    ) == ["http://host/dir/page", expected_target]


@pytest.mark.parametrize(
    "action, expected_target",
    [
        pytest.param("", "http://host/dir/page?a=1", id="empty"),
        pytest.param("submit?b=2#frag", "http://host/dir/submit?a=1", id="own query"),
    ],
)
def test_raise_host_state_replaces_query_of_get_action(action: str, expected_target: str) -> None:
    assert _submit_form(
        f'<form method="get" action="{action}"><input name="a" value="1"></form>',
        "/dir/page?lang=en",
    ) == ["http://host/dir/page?lang=en", expected_target]

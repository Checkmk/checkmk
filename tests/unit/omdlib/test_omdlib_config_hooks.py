#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from omdlib import config_hooks, main


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(
            "0.0.0.0",
            id="IP4 address.",
        ),
        pytest.param(
            "0.0.0.0 ::",
            id="Accept all IP4 & IP6 addresses.",
            marks=pytest.mark.xfail(reason="IPv6 is not implemented. SUP-10011"),
        ),
        pytest.param(
            "1::",
            id="Specify two IP6 addresses.",
            marks=pytest.mark.xfail(reason="IPv6 is not implemented. SUP-10011"),
        ),
        pytest.param(
            "0.0.0.0 ::/0",
            id="Default value.",
            marks=pytest.mark.xfail(reason="IPv6 is not implemented. SUP-10011"),
        ),
    ],
)
def test__error_from_config_choice_accept_value(value: str) -> None:
    assert main._error_from_config_choice(config_hooks.IpAddressListHasError(), value).is_ok()


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(
            "६.६.६.६",
            id="Originally valid in Checkmk (but not with xinitd. I kind of want to keep it.",
            marks=pytest.mark.xfail(reason="Some fun with unicode digits."),
        ),
        pytest.param(
            "",
            id="This value is needed (I think).",
        ),
        pytest.param(
            "0.0.0.00.0.0.0",
            id="Somebody forgot a whitespace :( ",
            marks=pytest.mark.xfail(reason="Regex is hard."),
        ),
        pytest.param(
            "a::::a",
            id="Invalid ip6 address.",
        ),
        pytest.param(
            "a::b::c",
            id="Invalid ip6 address.",
        ),
        pytest.param(
            ":::",
            id="Invalid ip6 address.",
        ),
    ],
)
def test__error_from_config_choice_reject_value(value: str) -> None:
    assert main._error_from_config_choice(config_hooks.IpAddressListHasError(), value).is_error()

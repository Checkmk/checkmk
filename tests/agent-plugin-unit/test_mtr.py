#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import pytest

if sys.version_info[0] == 2:
    import agents.plugins.mtr_2 as mtr  # pylint: disable=syntax-error
else:
    from agents.plugins import mtr


@pytest.mark.parametrize(
    "host, expected_result",
    [
        pytest.param(
            "abc123",
            "abc123",
            id="simple case",
        ),
        pytest.param(
            "abc{123}&%",
            "abc-123",
            id="with funny characters",
        ),
    ],
)
def test_host_to_filename(host: str, expected_result: str) -> None:
    assert mtr.host_to_filename(host) == expected_result


@pytest.mark.parametrize(
    "host, expected_result",
    [
        pytest.param("www.google.com", "www.google.com", id="plain host name"),
        pytest.param("192.168.1.1", "192.168.1.1", id="IPv4 address"),
        pytest.param("2001:db8::1", "2001:db8::1", id="IPv6 address"),
        pytest.param("foo.example.com (IPv6)", "foo.example.com", id="with derived suffix"),
        pytest.param(
            "2001:db8::1 (TCP port 8080)", "2001:db8::1", id="suffix built from several settings"
        ),
    ],
)
def test_mtr_target(host: str, expected_result: str) -> None:
    assert mtr.mtr_target(host) == expected_result

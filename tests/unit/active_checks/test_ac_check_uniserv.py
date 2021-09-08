#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access,redefined-outer-name
import pytest

from tests.testlib import import_module  # pylint: disable=import-error


@pytest.fixture(scope="module")
def check_uniserv():
    return import_module("active_checks/check_uniserv")


@pytest.mark.parametrize(
    "args",
    [
        [],
        [
            "host",
        ],
        ["host", "port"],
        ["host", "port", "service"],
        ["host", "port", "service", "ADDRESS"],
        ["host", "port", "service", "ADDRESS", "street"],
        ["host", "port", "service", "ADDRESS", "street", "street_nr"],
        ["host", "port", "service", "ADDRESS", "street", "street_nr", "city", "regex"],
    ],
)
def test_ac_check_uniserv_broken_arguments(capsys, check_uniserv, args):
    with pytest.raises(SystemExit):
        check_uniserv.parse_arguments(args)
    out, _err = capsys.readouterr()
    assert (
        out
        == " Usage: check_uniserv HOSTNAME PORT SERVICE (VERSION|ADDRESS STREET NR CITY SEARCH_REGEX)\n"
    )


@pytest.mark.parametrize(
    "args, expected_args",
    [
        (
            ["host", "123", "service", "job"],
            ("host", 123, "service", "job", None, None, None, None),
        ),
        (
            ["host", "123", "service", "ADDRESS", "street", "street_nr", "city", "regex"],
            ("host", 123, "service", "ADDRESS", "street", "street_nr", "city", "regex"),
        ),
    ],
)
def test_ac_check_uniserv_parse_arguments(check_uniserv, args, expected_args):
    assert check_uniserv.parse_arguments(args) == expected_args


@pytest.mark.parametrize(
    "data",
    [
        "",
        ";",
        "=;",
        ";=",
        "foo=bar",
        "type=TIPTOP",
        "foo=bar;",
        "foo=bar;type=TIPTOP",
        "foo=bar;type=TIPTOP",
    ],
)
def test_ac_check_uniserv_broken_data(capsys, check_uniserv, data):
    with pytest.raises(SystemExit):
        check_uniserv.parse_response(data)
    out, _err = capsys.readouterr()
    assert out.startswith("Invalid data:")


@pytest.mark.parametrize(
    "data",
    [
        "type=1;",
        "type=1;foo=bar",
    ],
)
def test_ac_check_uniserv_broken_response(capsys, check_uniserv, data):
    with pytest.raises(SystemExit):
        check_uniserv.parse_response(data)
    out, _err = capsys.readouterr()
    assert out.startswith("Invalid response:")


@pytest.mark.parametrize(
    "data, expected_result",
    [
        ("type=TIPTOP;foo=bar", {"type": "TIPTOP"}),
        ("type=TIPTOP;key=value;foo=bar", {"type": "TIPTOP", "key": "value"}),
    ],
)
def test_ac_check_uniserv_parse_response(check_uniserv, data, expected_result):
    assert sorted(check_uniserv.parse_response(data).items()) == sorted(expected_result.items())


@pytest.mark.parametrize(
    "args, parsed, expected_result",
    [
        ((None, None, "SID", None, None, None, None), {}, (3, "Unknown job")),
        (("VERSION", None, "SID", None, None, None, None), {}, (3, "Unknown version")),
        (
            ("VERSION", None, "SID", None, None, None, None),
            {"version_str": "123"},
            (0, "Version: 123"),
        ),
        (("ADDRESS", None, "SID", None, None, None, ""), {}, (3, "Unknown zip or city")),
        (
            ("ADDRESS", None, "SID", None, None, None, ""),
            {
                "out_zip": "456",
            },
            (3, "Unknown zip or city"),
        ),
        (
            ("ADDRESS", None, "SID", None, None, None, ""),
            {
                "out_city": "Muc",
            },
            (3, "Unknown zip or city"),
        ),
        (
            ("ADDRESS", None, "SID", None, None, None, ""),
            {"out_zip": "456", "out_city": "Muc"},
            (0, "Address: 456 Muc"),
        ),
        (
            ("ADDRESS", None, "SID", None, None, None, "Ber"),
            {"out_zip": "456", "out_city": "Muc"},
            (2, "Address: 456 Muc but expects Ber"),
        ),
    ],
)
def test_ac_check_uniserv_check_job(monkeypatch, check_uniserv, args, parsed, expected_result):
    job, s, sid, street, street_nr, city, regex = args
    monkeypatch.setattr("check_uniserv.send_and_receive", lambda x, y: parsed)
    assert check_uniserv.check_job(job, s, sid, street, street_nr, city, regex) == expected_result

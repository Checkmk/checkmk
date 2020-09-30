#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.gui.config
from cmk.gui.exceptions import MKUserError
import cmk.gui.valuespec as vs
from testlib import on_time


@pytest.mark.parametrize("entry, result", [
    ("m0", ((1567296000.0, 1567702200.0), "September 2019")),
    ("m1", ((1564617600.0, 1567296000.0), "August 2019")),
    ("m3", ((1559347200.0, 1567296000.0), u"June 2019 — August 2019")),
    ("y1", ((1514764800.0, 1546300800.0), "2018")),
    ("y0", ((1546300800.0, 1567702200.0), "2019")),
    ("4h", ((1567687800.0, 1567702200.0), u"Last 4 hours")),
    (4 * 60 * 60, ((1567687800.0, 1567702200.0), "The last 4 hours")),
    ("25h", ((1567612200.0, 1567702200.0), u"Last 25 hours")),
    ("8d", ((1567011000.0, 1567702200.0), u"Last 8 days")),
    ("15d", ((1566406200.0, 1567702200.0), u"Last 15 days")),
    ("35d", ((1564678200.0, 1567702200.0), u"Last 35 days")),
    ("400d", ((1533142200.0, 1567702200.0), u"Last 400 days")),
    ("d0", ((1567641600.0, 1567702200.0), u"Today")),
    ("d1", ((1567555200.0, 1567641600.0), u"Yesterday")),
    ("d7", ((1567036800.0, 1567123200.0), u"2019-08-29")),
    ("d8", ((1566950400.0, 1567036800.0), u"2019-08-28")),
    ("w0", ((1567382400.0, 1567702200.0), u"This week")),
    ("w1", ((1566777600.0, 1567382400.0), u"Last week")),
    ("w2", ((1566172800.0, 1566777600.0), u"2019-08-19 — 2019-08-25")),
    (("date", (1536098400.0, 1567288800.0)),
     ((1536098400.0, 1567375200.0), u"2018-09-04 — 2019-09-01")),
    (("until", 1577232000), ((1567702200.0, 1577232000.0), u"2019-12-25")),
    (("time", (1549374782.0, 1567687982.0)),
     ((1549374782.0, 1567687982.0), u"2019-02-05 — 2019-09-05")),
    (("age", 2 * 3600), ((1567695000.0, 1567702200.0), u"The last 2 hours")),
    (("next", 3 * 3600), ((1567702200.0, 1567713000.0), u"The next 3 hours")),
])
def test_timerange(entry, result):
    with on_time("2019-09-05 16:50", "UTC"):
        assert vs.Timerange().compute_range(entry) == result


@pytest.mark.parametrize("entry, refutcdate, result", [
    ("m0", "2019-09-15 15:09", ((1567296000.0, 1568560140.0), "September 2019")),
    ("m1", "2019-01-12", ((1543622400.0, 1546300800.0), "December 2018")),
    ("m-1", "2019-09-15 15:09", ((1567296000.0, 1569888000.0), "September 2019")),
    ("m2", "2019-02-12", ((1543622400.0, 1548979200.0), u"December 2018 — January 2019")),
    ("m3", "2019-02-12", ((1541030400.0, 1548979200.0), u"November 2018 — January 2019")),
    ("m-3", "2019-02-12", ((1548979200.0, 1556668800.0), u"February 2019 — April 2019")),
    ("m-3", "2018-12-12", ((1543622400.0, 1551398400.0), u"December 2018 — February 2019")),
    ("m6", "2019-02-12", ((1533081600.0, 1548979200.0), u"August 2018 — January 2019")),
    ("m-6", "2019-02-12", ((1548979200.0, 1564617600.0), u"February 2019 — July 2019")),
    ("y0", "2019-09-15", ((1546300800.0, 1568505600.0), "2019")),
    ("y1", "2019-09-15", ((1514764800.0, 1546300800.0), "2018")),
    ("y-1", "2019-09-15", ((1546300800.0, 1577836800.0), "2019")),
    ("f0", "2020-01-25", ((1577836800.0, 1577923200.0), "01/01/2020")),
    ("f1", "2020-01-25", ((1575158400.0, 1575244800.0), "01/12/2019")),
    ("l1", "2020-01-25", ((1577750400.0, 1577836800.0), "31/12/2019")),
    ("l1", "2020-03-25", ((1582934400.0, 1583020800.0), "29/02/2020")),
])
def test_timerange2(entry, refutcdate, result):
    with on_time(refutcdate, "UTC"):
        assert vs.Timerange().compute_range(entry) == result


@pytest.mark.parametrize("args, result", [
    ((1546300800, 1, "m"), 1548979200),
    ((1546300800, 3, "m"), 1554076800),
    ((1546300800, -1, "m"), 1543622400),
    ((1546300800, -2, "m"), 1541030400),
    ((1546300800, -3, "m"), 1538352000),
    ((1538352000, 3, "m"), 1546300800),
    ((1546300800, -6, "m"), 1530403200),
])
def test_timehelper_add(args, result):
    with on_time("2019-09-05", "UTC"):
        assert vs.TimeHelper.add(*args) == result


@pytest.mark.parametrize("value, result", [
    (-1580000000, "1919-12-07"),
    (1, "1970-01-01"),
    (1580000000, "2020-01-26"),
    (1850000000, "2028-08-16"),
])
def test_absolutedate_value_to_json_conversion(value, result):
    with on_time("2020-03-02", "UTC"):
        assert vs.AbsoluteDate().value_to_text(value) == result
        json_value = vs.AbsoluteDate().value_to_json(value)
        assert vs.AbsoluteDate().value_from_json(json_value) == value


@pytest.mark.parametrize("value, result", [
    ((1582671600, 1582844400), "2020-02-25, 2020-02-27"),
    ((1577833200, 1580425200), "2019-12-31, 2020-01-30"),
])
def test_tuple_value_to_json_conversion(value, result):
    with on_time("2020-03-02", "UTC"):
        assert vs.Tuple([vs.AbsoluteDate(), vs.AbsoluteDate()]).value_to_text(value) == result
        json_value = vs.Tuple([vs.AbsoluteDate(), vs.AbsoluteDate()]).value_to_json(value)
        assert vs.Tuple([vs.AbsoluteDate(), vs.AbsoluteDate()]).value_from_json(json_value) == value


@pytest.mark.parametrize("value, result", [
    (120, "2 minutes"),
    (700, "11 minutes 40 seconds"),
    (7580, "2 hours 6 minutes 20 seconds"),
    (527500, "6 days 2 hours 31 minutes 40 seconds"),
])
def test_age_value_to_json_conversion(value, result):
    assert vs.Age().value_to_text(value) == result
    json_value = vs.Age().value_to_json(value)
    assert vs.Age().value_from_json(json_value) == value


@pytest.mark.parametrize("choices, value, result", [
    ([(0, "OK"), (1, "WARN"), (2, "CRIT"), (3, "UNKN")], 2, "CRIT"),
    ([("h", "Show alerts per hour"), ("d", "Show alerts per day")], "h", "Show alerts per hour"),
])
def test_dropdownchoice_value_to_json_conversion(choices, value, result):
    assert vs.DropdownChoice(choices).value_to_text(value) == result
    json_value = vs.DropdownChoice(choices).value_to_json(value)
    assert vs.DropdownChoice(choices).value_from_json(json_value) == value


@pytest.mark.parametrize(
    "value, result_title",
    [
        (("age", 4 * 60 * 60), "The last 4 fun hours"),  # Werk 4477, deprecated input on cmk2.0
        (("age", 25 * 60 * 60), "The last 25 hard hours"),  # Werk 4477, deprecated input on cmk2.0
        (4 * 60 * 60, "The last 4 fun hours"),  # defaults are idents
        (25 * 60 * 60, "The last 25 hard hours"),  # defaults are idents
        (3600 * 24 * 7 * 1.5, "Since a sesquiweek"),  # defaults are idents
    ])
def test_timerange_value_to_text_conversion(monkeypatch, value, result_title):

    monkeypatch.setattr(cmk.gui.config, "graph_timeranges", [{
        'title': "The last 4 fun hours",
        "duration": 4 * 60 * 60
    }, {
        'title': "The last 25 hard hours",
        "duration": 25 * 60 * 60
    }, {
        "title": "Since a sesquiweek",
        "duration": 3600 * 24 * 7 * 1.5
    }])

    assert vs.Timerange().value_to_text(value) == result_title


def test_timerange_value_to_json_conversion():
    with on_time("2020-03-02", "UTC"):
        for ident, title, _vs in vs.Timerange().choices():
            choice_value: vs.CascadingDropdownChoiceValue = ident
            if ident == "age":
                choice_value = ("age", 12345)
                title = "The last..., 3 hours 25 minutes 45 seconds"
            elif ident == "date":
                choice_value = ("date", (1582671600.0, 1582844400.0))
                title = "Date range, 2020-02-25, 2020-02-27"

            assert vs.Timerange().value_to_text(choice_value) == title
            json_value = vs.Timerange().value_to_json(choice_value)
            assert vs.Timerange().value_from_json(json_value) == choice_value


@pytest.mark.parametrize("value, result", [
    ({
        "time_range": ("date", (1577833200, 1580425200)),
        "time_resolution": "h"
    }, "Time range: Date range, 2019-12-31, 2020-01-30, Time resolution: Show alerts per hour"),
    ({
        "time_range": ("age", 158000),
        "time_resolution": "d"
    },
     "Time range: The last..., 1 days 19 hours 53 minutes 20 seconds, Time resolution: Show alerts per day"
    ),
])
def test_dictionary_value_to_json_conversion(value, result):
    with on_time("2020-03-02", "UTC"):
        # TODO: Obtain this valuespec directly by importing AlertBarChartDashlet
        #       once it's available and simplify to:
        #       abcd_vs = AlertBarChartDashlet.vs_parameters()
        abcd_vs = vs.Dictionary([
            ("time_range", vs.Timerange(title="Time range")),
            ("time_resolution",
             vs.DropdownChoice(title="Time resolution",
                               choices=[("h", "Show alerts per hour"),
                                        ("d", "Show alerts per day")])),
        ])
        abcd_vs._render = "oneline"
        assert abcd_vs.value_to_text(value) == result
        json_value = abcd_vs.value_to_json(value)
        assert abcd_vs.value_from_json(json_value) == value


@pytest.mark.parametrize(
    "address",
    [
        "user@localhost",
        "harri.hirsch@example.com",
        "!#$%&'*+-=?^_`{|}~@c.de",  # other printable ASCII characters
        u"user@localhost",
        u"harri.hirsch@example.com",
        u"!#$%&'*+-=?^_`{|}~@c.de",
        u"אሗ@test.de",  # non-ASCII characters
    ])
def test_email_validation(address):
    vs.EmailAddress().validate_value(address, "")


@pytest.mark.parametrize("address", [
    "a..b@c.de",
    "ab@c..de",
    u"a..b@c.de",
    u"ab@c..de",
])
def test_email_validation_non_compliance(address):
    # TODO: validate_value should raise an exception in these
    #       cases since subsequent dots without any ASCII
    #       character in between are not allowed in RFC5322.
    vs.EmailAddress().validate_value(address, "")


@pytest.mark.parametrize(
    "address",
    [
        b"text",
        b"user@foo",
        b"\t\n a@localhost \t\n",  # whitespace is removed in from_html_vars
        u"אሗ@test.com".encode("utf-8"),  # UTF-8 encoded bytestrings are not allowed
        u"text",
        u"user@foo",
        u"\t\n a@localhost \t\n",  # whitespace is removed in from_html_vars
    ])
def test_email_validation_raises(address):
    with pytest.raises(MKUserError):
        vs.EmailAddress().validate_value(address, "")

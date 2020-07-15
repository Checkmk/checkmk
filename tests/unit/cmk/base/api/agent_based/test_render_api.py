#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import inspect
import time
import pytest  # type: ignore[import]
import cmk.base.api.agent_based.render as render


def _test_render_func(f, result, *args, **kwargs):
    if inspect.isclass(result) and issubclass(result, Exception):
        with pytest.raises(result):
            f(*args, **kwargs)
    else:
        assert f(*args, **kwargs) == result


@pytest.mark.parametrize("epoch, output", [
    (0, "Jan 01 1970"),
    (1587908220, "Apr 26 2020"),
    (1587908220.0, "Apr 26 2020"),
    ("1587908220", "Apr 26 2020"),
])
def test_date(epoch, output):
    _test_render_func(render.date, output, epoch=epoch)


@pytest.mark.parametrize("epoch, output", [
    (0, "Jan 01 1970 00:00:00"),
    (1587908220, "Apr 26 2020 13:37:00"),
    (1587908220.0, "Apr 26 2020 13:37:00"),
    ("1587908220", "Apr 26 2020 13:37:00"),
])
def test_datetime(monkeypatch, epoch, output):
    monkeypatch.setattr(time, "localtime", time.gmtime)
    _test_render_func(render.datetime, output, epoch=epoch)


@pytest.mark.parametrize("seconds, output", [
    (0, "0 seconds"),
    (0.00000001, "10 nanoseconds"),
    (0.1, "100 milliseconds"),
    (22, "22 seconds"),
    (158, "2 minutes 38 seconds"),
    (98, "1 minute 38 seconds"),
    (1234567, "14 days 6 hours"),
    (31536001, "1 year 0 days"),
    (-1231.213, ValueError),
])
def test_timespan(seconds, output):
    _test_render_func(render.timespan, output, seconds=seconds)


@pytest.mark.parametrize("value, output", [
    (0, 1),
    (1, 1),
    (45.123123, 2),
    (1e3, 4),
    (1e5, 6),
    (-2, ValueError),
])
def test__digits_left(value, output):
    _test_render_func(render._digits_left, output, value)


@pytest.mark.parametrize("value, use_si_units, output", [
    (0, True, ("0.00", "B")),
    (1, True, ("1.00", "B")),
    (101.123, True, ("101", "B")),
    (101.623, True, ("102", "B")),
    (1000.0, True, ("1.00", "KB")),
    (10001.623, True, ("10.0", "KB")),
    (100000.0, True, ("100", "KB")),
    (0, False, ("0.00", "B")),
    (-123.123, True, ValueError),
])
def test__auto_scale(value, use_si_units, output):
    _test_render_func(render._auto_scale, output, value, use_si_units)


@pytest.mark.parametrize("bytes_, output", [
    (0, "0 B"),
    (1, "1 B"),
    (2345, "2.35 KB"),
    (1024**2, "1.05 MB"),
    (1000**2, "1.00 MB"),
    (1234000, "1.23 MB"),
    (12340006, "12.3 MB"),
    (123400067, "123 MB"),
    (1234000678, "1.23 GB"),
    (-17408, ValueError),
])
def test_disksize(bytes_, output):
    _test_render_func(render.disksize, output, bytes_)


@pytest.mark.parametrize("bytes_, output", [
    (0, "0 B"),
    (1, "1 B"),
    (2345, "2.29 KiB"),
    (1024**2, "1.00 MiB"),
    (1000**2, "977 KiB"),
    (1234000, "1.18 MiB"),
    (12340006, "11.8 MiB"),
    (123400067, "118 MiB"),
    (1234000678, "1.15 GiB"),
    (-17408, ValueError),
])
def test_bytes(bytes_, output):
    _test_render_func(render.bytes, output, bytes_)


@pytest.mark.parametrize("bytes_, output", [
    (0, "0 B"),
    (1, "1 B"),
    (2345, "2,345 B"),
    (1024**2, "1,048,576 B"),
    (1000**2, "1,000,000 B"),
    (1234000678, "1,234,000,678 B"),
])
def test_filesize(bytes_, output):
    _test_render_func(render.filesize, output, bytes_)


@pytest.mark.parametrize("octets_per_sec, output", [
    (0, "0 Bit/s"),
    (1, "8 Bit/s"),
    (2345, "18.8 KBit/s"),
    (1.25 * 10**5, "1 MBit/s"),
    (1.25 * 10**6, "10 MBit/s"),
    (1.25 * 10**7, "100 MBit/s"),
    (1234000678, "9.87 GBit/s"),
    (-129873.2398409, ValueError),
])
def test_nicspeed(octets_per_sec, output):
    _test_render_func(render.nicspeed, output, octets_per_sec)


@pytest.mark.parametrize("octets_per_sec, output", [
    (0, "0.00 Bit/s"),
    (1, "8.00 Bit/s"),
    (2345, "18.8 KBit/s"),
    (1.25 * 10**5, "1.00 MBit/s"),
    (1.25 * 10**6, "10.0 MBit/s"),
    (1.25 * 10**7, "100 MBit/s"),
    (1234000678, "9.87 GBit/s"),
    (-999, ValueError),
])
def test_networkbandwitdh(octets_per_sec, output):
    _test_render_func(render.networkbandwidth, output, octets_per_sec)


@pytest.mark.parametrize("bytes_, output", [
    (0, "0.00 B/s"),
    (1, "1.00 B/s"),
    (2345, "2.35 KB/s"),
    (1024**2, "1.05 MB/s"),
    (1000**2, "1.00 MB/s"),
    (1234000678, "1.23 GB/s"),
    (-999, ValueError),
])
def test_iobandwidth(bytes_, output):
    _test_render_func(render.iobandwidth, output, bytes_)


@pytest.mark.parametrize("percentage, output", [
    (0., "0%"),
    (0.001, "0.00%"),
    (0.01, "0.01%"),
    (1.0, "1.00%"),
    (10, "10.0%"),
    (99.8, "99.8%"),
    (99.9, "99.90%"),
    (99.92, "99.92%"),
    (99.9991, "99.9991%"),
    (99.9997, "99.9997%"),
    (100, "100%"),
    (100.01, "100%"),
    (100, "100%"),
    (123, "123%"),
    (-23, ValueError),
])
def test_percent(percentage, output):
    _test_render_func(render.percent, output, percentage)

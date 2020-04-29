#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest  # type: ignore[import]
import time
import cmk.base.api.agent_based.render as render


@pytest.mark.parametrize("epoch, output", [
    (0, "Jan 01 1970"),
    (1587908220, "Apr 26 2020"),
    (1587908220.0, "Apr 26 2020"),
    ("1587908220", "Apr 26 2020"),
])
def test_date(epoch, output):
    assert render.date(epoch=epoch) == output


@pytest.mark.parametrize("epoch, output", [
    (0, "Jan 01 1970 00:00:00"),
    (1587908220, "Apr 26 2020 13:37:00"),
    (1587908220.0, "Apr 26 2020 13:37:00"),
    ("1587908220", "Apr 26 2020 13:37:00"),
])
def test_datetime(monkeypatch, epoch, output):
    monkeypatch.setattr(time, "localtime", time.gmtime)
    assert render.datetime(epoch=epoch) == output


@pytest.mark.parametrize("seconds, output", [
    (0.00000001, "10 nanoseconds"),
    (0.1, "100 milliseconds"),
    (22, "22 seconds"),
    (158, "2 minutes 38 seconds"),
    (98, "1 minute 38 seconds"),
    (1234567, "14 days 6 hours"),
    (31536001, "1 year 0 days"),
])
def test_timespan(seconds, output):
    assert render.timespan(seconds=seconds) == output


@pytest.mark.parametrize("bytes_, output", [
    (1, "1 B"),
    (2345, "2.35 KB"),
    (1024**2, "1.05 MB"),
    (1000**2, "1.00 MB"),
    (1234000, "1.23 MB"),
    (12340006, "12.3 MB"),
    (123400067, "123 MB"),
    (1234000678, "1.23 GB"),
])
def test_disksize(bytes_, output):
    assert render.disksize(bytes_) == output


@pytest.mark.parametrize("bytes_, output", [
    (1, "1 B"),
    (2345, "2.29 KiB"),
    (1024**2, "1.00 MiB"),
    (1000**2, "977 KiB"),
    (1234000, "1.18 MiB"),
    (12340006, "11.8 MiB"),
    (123400067, "118 MiB"),
    (1234000678, "1.15 GiB"),
])
def test_bytes(bytes_, output):
    assert render.bytes(bytes_) == output


@pytest.mark.parametrize("bytes_, output", [
    (1, "1 B"),
    (2345, "2,345 B"),
    (1024**2, "1,048,576 B"),
    (1000**2, "1,000,000 B"),
    (1234000678, "1,234,000,678 B"),
])
def test_filesize(bytes_, output):
    assert render.filesize(bytes_) == output


@pytest.mark.parametrize("octets_per_sec, output", [
    (1, "8 Bit/s"),
    (2345, "18.8 KBit/s"),
    (1.25 * 10**5, "1 MBit/s"),
    (1.25 * 10**6, "10 MBit/s"),
    (1.25 * 10**7, "100 MBit/s"),
    (1234000678, "9.87 GBit/s"),
])
def test_nicspeed(octets_per_sec, output):
    assert render.nicspeed(octets_per_sec) == output


@pytest.mark.parametrize("octets_per_sec, output", [
    (1, "8.00 Bit/s"),
    (2345, "18.8 KBit/s"),
    (1.25 * 10**5, "1.00 MBit/s"),
    (1.25 * 10**6, "10.0 MBit/s"),
    (1.25 * 10**7, "100 MBit/s"),
    (1234000678, "9.87 GBit/s"),
])
def test_networkbandwitdh(octets_per_sec, output):
    assert render.networkbandwidth(octets_per_sec) == output


@pytest.mark.parametrize("bytes_, output", [
    (1, "1.00 B/s"),
    (2345, "2.35 KB/s"),
    (1024**2, "1.05 MB/s"),
    (1000**2, "1.00 MB/s"),
    (1234000678, "1.23 GB/s"),
])
def test_iobandwidth(bytes_, output):
    assert render.iobandwidth(bytes_) == output


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
])
def test_percent(percentage, output):
    assert render.percent(percentage) == output

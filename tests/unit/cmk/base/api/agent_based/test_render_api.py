#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

import cmk.base.api.agent_based.render as render


@pytest.mark.parametrize(
    "epoch, output",
    [
        (0, "Jan 01 1970"),
        (1587908220, "Apr 26 2020"),
        (1587908220.0, "Apr 26 2020"),
        ("1587908220", "Apr 26 2020"),
    ],
)
def test_date(epoch, output) -> None:
    assert output == render.date(epoch=epoch)


@pytest.mark.parametrize(
    "epoch, output",
    [
        (0, "Jan 01 1970 00:00:00"),
        (1587908220, "Apr 26 2020 13:37:00"),
        (1587908220.0, "Apr 26 2020 13:37:00"),
        ("1587908220", "Apr 26 2020 13:37:00"),
    ],
)
def test_datetime(monkeypatch, epoch, output) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)
    assert output == render.datetime(epoch=epoch)


@pytest.mark.parametrize(
    "seconds, output",
    [
        (0, "0 seconds"),
        (0.00000001, "10 nanoseconds"),
        (5.3991e-05, "54 microseconds"),
        (0.1, "100 milliseconds"),
        (22, "22 seconds"),
        (158, "2 minutes 38 seconds"),
        (98, "1 minute 38 seconds"),
        (1234567, "14 days 6 hours"),
        (31536001, "1 year 0 days"),
    ],
)
def test_timespan(seconds, output) -> None:
    assert output == render.timespan(seconds=seconds)


def test_timespan_negative() -> None:
    with pytest.raises(ValueError):
        _ = render.timespan(seconds=-1.0)


@pytest.mark.parametrize(
    "value, output",
    [
        (0, 1),
        (1, 1),
        (45.123123, 2),
        (1e3, 4),
        (1e5, 6),
        (-2, 1),
    ],
)
def test__digits_left(value, output) -> None:
    assert output == render._digits_left(value)


@pytest.mark.parametrize(
    "value, use_si_units, output",
    [
        (0, True, ("0.00", "B")),
        (1, True, ("1.00", "B")),
        (101.123, True, ("101", "B")),
        (101.623, True, ("102", "B")),
        (1000.0, True, ("1.00", "kB")),
        (10001.623, True, ("10.0", "kB")),
        (100000.0, True, ("100", "kB")),
        (0, False, ("0.00", "B")),
        (-123.123, True, ("-123", "B")),
    ],
)
def test__auto_scale(value, use_si_units, output) -> None:
    assert output == render._auto_scale(value, use_si_units)


@pytest.mark.parametrize(
    "bytes_, output",
    [
        (0, "0 B"),
        (1, "1 B"),
        (2345, "2.35 kB"),
        (1024**2, "1.05 MB"),
        (1000**2, "1.00 MB"),
        (1234000, "1.23 MB"),
        (12340006, "12.3 MB"),
        (123400067, "123 MB"),
        (1234000678, "1.23 GB"),
        (-17408, "-17.4 kB"),
    ],
)
def test_disksize(bytes_, output) -> None:
    assert output == render.disksize(bytes_)


@pytest.mark.parametrize(
    "bytes_, output",
    [
        (0, "0 B"),
        (1, "1 B"),
        (2345, "2.29 KiB"),
        (1024**2, "1.00 MiB"),
        (1000**2, "977 KiB"),
        (1234000, "1.18 MiB"),
        (12340006, "11.8 MiB"),
        (123400067, "118 MiB"),
        (1234000678, "1.15 GiB"),
        (-17408, "-17.0 KiB"),
    ],
)
def test_bytes(bytes_, output) -> None:
    assert output == render.bytes(bytes_)


@pytest.mark.parametrize(
    "bytes_, output",
    [
        (0, "0 B"),
        (1, "1 B"),
        (2345, "2,345 B"),
        (1024**2, "1,048,576 B"),
        (1000**2, "1,000,000 B"),
        (600000, "600,000 B"),
        (1234000678, "1,234,000,678 B"),
        (-1234000678, "-1,234,000,678 B"),
    ],
)
def test_filesize(bytes_, output) -> None:
    assert output == render.filesize(bytes_)


@pytest.mark.parametrize(
    "octets_per_sec, output",
    [
        (0, "0 Bit/s"),
        (1, "8 Bit/s"),
        (2345, "18.8 kBit/s"),
        (1.25 * 10**5, "1 MBit/s"),
        (1.25 * 10**6, "10 MBit/s"),
        (1.25 * 10**7, "100 MBit/s"),
        (1234000678, "9.87 GBit/s"),
        (-1234000678, "-9.87 GBit/s"),
    ],
)
def test_nicspeed(octets_per_sec, output) -> None:
    assert output == render.nicspeed(octets_per_sec)


@pytest.mark.parametrize(
    "octets_per_sec, output",
    [
        (0, "0.00 Bit/s"),
        (1, "8.00 Bit/s"),
        (2345, "18.8 kBit/s"),
        (1.25 * 10**5, "1.00 MBit/s"),
        (1.25 * 10**6, "10.0 MBit/s"),
        (1.25 * 10**7, "100 MBit/s"),
        (-1.25 * 10**7, "-100 MBit/s"),
        (1234000678, "9.87 GBit/s"),
        (-1234000678, "-9.87 GBit/s"),
    ],
)
def test_networkbandwitdh(octets_per_sec, output) -> None:
    assert output == render.networkbandwidth(octets_per_sec)


@pytest.mark.parametrize(
    "bytes_, output",
    [
        (0, "0.00 B/s"),
        (1, "1.00 B/s"),
        (2345, "2.35 kB/s"),
        (1024**2, "1.05 MB/s"),
        (1000**2, "1.00 MB/s"),
        (-(1000**2), "-1.00 MB/s"),
        (1234000678, "1.23 GB/s"),
        (-1234000678, "-1.23 GB/s"),
    ],
)
def test_iobandwidth(bytes_, output) -> None:
    assert output == render.iobandwidth(bytes_)


@pytest.mark.parametrize(
    "percentage, output",
    [
        # 1. Die 0 selbst:
        (0.0, "0%"),
        # 2. Bereich ]0, 0.01[:
        (0.000102, "<0.01%"),
        # 3. Bereich [1 ... 99]:
        # -> Ausgabe mit 2 Nachkommastellen
        (1.0, "1.00%"),
        (1.234, "1.23%"),
        (10.80, "10.80%"),
        (99.92, "99.92%"),
        # 5. Bereich [100,
        (100.01, "100.01%"),
        (123.456, "123.46%"),
    ],
)
def test_percent(percentage, output) -> None:
    assert output == render.percent(percentage)
    # 6. Bereich kleiner 0:
    #     negieren und "-" davorhängen
    if abs(percentage) >= 0.01:
        assert f"-{output}" == render.percent(-percentage)


@pytest.mark.parametrize(
    "hz, output",
    [
        (111, "111 Hz"),
        (1112, "1.11 kHz"),
        (111222, "111 kHz"),
        (111222333, "111 MHz"),
        (111222333444, "111 GHz"),
    ],
)
def test_frequency(hz, output) -> None:
    assert output == render.frequency(hz)

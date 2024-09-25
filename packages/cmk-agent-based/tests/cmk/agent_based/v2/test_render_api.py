#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

import pytest

from cmk.agent_based.v2 import render


@pytest.mark.parametrize(
    "epoch, output",
    [
        (0, "1970-01-01"),
        (1587908220, "2020-04-26"),
        (1587908220.0, "2020-04-26"),
    ],
)
def test_date(epoch: float | None, output: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)
    assert output == render.date(epoch=epoch)


@pytest.mark.parametrize(
    "epoch, output",
    [
        (0, "1970-01-01 00:00:00"),
        (1587908220, "2020-04-26 13:37:00"),
        (1587908220.0, "2020-04-26 13:37:00"),
    ],
)
def test_datetime(epoch: float | None, output: str, monkeypatch: pytest.MonkeyPatch) -> None:
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
def test_timespan(seconds: float, output: str) -> None:
    assert output == render.timespan(seconds=seconds)


def test_timespan_negative() -> None:
    with pytest.raises(ValueError):
        _ = render.timespan(seconds=-1.0)


@pytest.mark.parametrize(
    "seconds, output",
    [
        (22, "22 seconds"),
        (-22, "-22 seconds"),
        (0, "0 seconds"),
        (-0, "0 seconds"),
    ],
)
def test_time_offset(seconds: float, output: str) -> None:
    assert output == render.time_offset(seconds)


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
def test_disksize(bytes_: float, output: str) -> None:
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
def test_bytes(bytes_: float, output: str) -> None:
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
def test_filesize(bytes_: float, output: str) -> None:
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
def test_nicspeed(octets_per_sec: float, output: str) -> None:
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
def test_networkbandwitdh(octets_per_sec: float, output: str) -> None:
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
def test_iobandwidth(bytes_: float, output: str) -> None:
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
def test_percent(percentage: float, output: str) -> None:
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
def test_frequency(hz: float, output: str) -> None:
    assert output == render.frequency(hz)

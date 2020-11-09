#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta

import cmk.utils.store as store
from cmk.utils.license_usage import (
    LicenseUsageSample,
    LicenseUsageHistoryDump,
    LicenseUsageHistoryDumpVersion,
)

import cmk.base.license_usage as license_usage

_license_usage_sample_example = LicenseUsageSample(
    version="",
    edition="",
    platform="",
    is_cma=False,
    sample_time=150,
    timezone="",
    num_hosts=100,
    num_services=1000,
)


def test_update_history_deserialize(monkeypatch):
    monkeypatch.setattr(store, "load_bytes_from_file", lambda p, default: b"{}")

    history_dump = license_usage._load_history_dump()
    assert history_dump.VERSION == LicenseUsageHistoryDumpVersion
    assert history_dump.history == []


def test_update_history_de_serialize(monkeypatch):
    history_dump = LicenseUsageHistoryDump(
        VERSION="1.1",
        history=[
            _license_usage_sample_example,
            LicenseUsageSample(
                version="Foo",
                edition="bär",
                platform="Test 123 - tßßßzz",
                is_cma=False,
                sample_time=75,
                timezone="",
                num_hosts=50,
                num_services=500,
            )
        ],
    )

    serialized_history_dump = history_dump.serialize()
    assert isinstance(serialized_history_dump, bytes)

    deserialized_history_dump = LicenseUsageHistoryDump.deserialize(serialized_history_dump)
    assert isinstance(deserialized_history_dump, LicenseUsageHistoryDump)

    assert history_dump.VERSION == deserialized_history_dump.VERSION
    assert deserialized_history_dump.VERSION == "1.1"

    assert history_dump.history == deserialized_history_dump.history
    assert len(deserialized_history_dump.history) == 2

    for (version, edition, platform, sample_time, num_hosts, num_services), sample in zip([
        ("", "", "", 150, 100, 1000),
        ("Foo", "bär", "Test 123 - tßßßzz", 75, 50, 500),
    ], deserialized_history_dump.history):
        assert sample.version == version
        assert sample.edition == edition
        assert sample.platform == platform
        assert sample.is_cma is False
        assert sample.sample_time == sample_time
        assert sample.timezone == ""
        assert sample.num_hosts == num_hosts
        assert sample.num_services == num_services


def test_update_history__create_or_update_history_dump_empty(monkeypatch):
    monkeypatch.setattr(store, "load_bytes_from_file", lambda p, default: b"{}")
    monkeypatch.setattr(
        license_usage,
        "_create_sample",
        lambda: _license_usage_sample_example,
    )

    history_dump = license_usage._create_or_update_history_dump()
    assert history_dump.VERSION == LicenseUsageHistoryDumpVersion
    assert len(history_dump.history) == 1

    sample = history_dump.history[0]
    assert sample.version == ""
    assert sample.edition == ""
    assert sample.platform == ""
    assert sample.is_cma is False
    assert sample.sample_time == 150
    assert sample.timezone == ""
    assert sample.num_hosts == 100
    assert sample.num_services == 1000


def test_update_history__create_or_update_history_dump(monkeypatch):
    serialized_history_dump = LicenseUsageHistoryDump(
        VERSION="1.2",
        history=[
            LicenseUsageSample(
                version="",
                edition="",
                platform="",
                is_cma=False,
                sample_time=3,
                timezone="",
                num_hosts=3,
                num_services=30,
            ),
            LicenseUsageSample(
                version="",
                edition="",
                platform="",
                is_cma=False,
                sample_time=2,
                timezone="",
                num_hosts=2,
                num_services=20,
            ),
            LicenseUsageSample(
                version="",
                edition="",
                platform="",
                is_cma=False,
                sample_time=1,
                timezone="",
                num_hosts=1,
                num_services=10,
            ),
        ],
    ).serialize()
    monkeypatch.setattr(store, "load_bytes_from_file", lambda p, default: serialized_history_dump)
    monkeypatch.setattr(
        license_usage,
        "_create_sample",
        lambda: _license_usage_sample_example,
    )

    history_dump = license_usage._create_or_update_history_dump()
    assert history_dump.VERSION == "1.2"
    assert len(history_dump.history) == 4

    for (sample_time, num_hosts, num_services), sample in zip([
        (150, 100, 1000),
        (3, 3, 30),
        (2, 2, 20),
        (1, 1, 10),
    ], history_dump.history):
        assert sample.version == ""
        assert sample.edition == ""
        assert sample.platform == ""
        assert sample.is_cma is False
        assert sample.sample_time == sample_time
        assert sample.timezone == ""
        assert sample.num_hosts == num_hosts
        assert sample.num_services == num_services


def test_update_history__may_update_successful(monkeypatch):
    fake_now = datetime(1970, 1, 2, 12, 0, 0)
    fake_next_run_ts = int((fake_now - timedelta(hours=1)).timestamp())

    monkeypatch.setattr(license_usage, "_last_update_try_ts",
                        (fake_now - timedelta(hours=1)).timestamp())

    # Check each condition
    assert not (fake_now.timestamp() - license_usage._last_update_try_ts) < 600
    assert not fake_now.timestamp() < fake_next_run_ts

    # Check result
    assert license_usage._may_update(fake_now.timestamp(), fake_next_run_ts)


def test_update_history__may_update_try_not_10min_ago(monkeypatch):
    fake_now = datetime(1970, 1, 2, 12, 0, 0)
    fake_next_run_ts = int((fake_now - timedelta(hours=1)).timestamp())

    monkeypatch.setattr(license_usage, "_last_update_try_ts",
                        (fake_now - timedelta(minutes=5)).timestamp())

    # Check each condition
    assert (fake_now.timestamp() - license_usage._last_update_try_ts) < 600
    assert not fake_now.timestamp() < fake_next_run_ts

    # Check result
    assert not license_usage._may_update(fake_now.timestamp(), fake_next_run_ts)


def test_update_history__may_update_next_run_not_reached(monkeypatch):
    fake_now = datetime(1970, 1, 2, 12, 0, 0)
    fake_next_run_ts = int((fake_now + timedelta(hours=1)).timestamp())

    monkeypatch.setattr(license_usage, "_last_update_try_ts",
                        (fake_now - timedelta(hours=1)).timestamp())

    # Check each condition
    assert not (fake_now.timestamp() - license_usage._last_update_try_ts) < 600
    assert fake_now.timestamp() < fake_next_run_ts

    # Check result
    assert not license_usage._may_update(fake_now.timestamp(), fake_next_run_ts)

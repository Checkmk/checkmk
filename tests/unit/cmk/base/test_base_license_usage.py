#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta

import pytest

from cmk.utils.license_usage.export import LicenseUsageExtensions

import cmk.base.license_usage as license_usage


def test_update_history__may_update_successful(monkeypatch):
    fake_now = datetime(1970, 1, 2, 12, 0, 0)
    fake_next_run_ts = int((fake_now - timedelta(hours=1)).timestamp())

    monkeypatch.setattr(
        license_usage, "_last_update_try_ts", (fake_now - timedelta(hours=1)).timestamp()
    )

    # Check each condition
    assert not (fake_now.timestamp() - license_usage._last_update_try_ts) < 600
    assert not fake_now.timestamp() < fake_next_run_ts

    # Check result
    assert license_usage._may_update(fake_now.timestamp(), fake_next_run_ts)


def test_update_history__may_update_try_not_10min_ago(monkeypatch):
    fake_now = datetime(1970, 1, 2, 12, 0, 0)
    fake_next_run_ts = int((fake_now - timedelta(hours=1)).timestamp())

    monkeypatch.setattr(
        license_usage, "_last_update_try_ts", (fake_now - timedelta(minutes=5)).timestamp()
    )

    # Check each condition
    assert (fake_now.timestamp() - license_usage._last_update_try_ts) < 600
    assert not fake_now.timestamp() < fake_next_run_ts

    # Check result
    assert not license_usage._may_update(fake_now.timestamp(), fake_next_run_ts)


def test_update_history__may_update_next_run_not_reached(monkeypatch):
    fake_now = datetime(1970, 1, 2, 12, 0, 0)
    fake_next_run_ts = int((fake_now + timedelta(hours=1)).timestamp())

    monkeypatch.setattr(
        license_usage, "_last_update_try_ts", (fake_now - timedelta(hours=1)).timestamp()
    )

    # Check each condition
    assert not (fake_now.timestamp() - license_usage._last_update_try_ts) < 600
    assert fake_now.timestamp() < fake_next_run_ts

    # Check result
    assert not license_usage._may_update(fake_now.timestamp(), fake_next_run_ts)


@pytest.mark.parametrize(
    "num_hosts, num_hosts_excluded, num_services, num_services_excluded, returns_sample",
    [
        (0, 0, 0, 0, False),
        (1, 0, 0, 0, True),
        (0, 1, 0, 0, True),
        (0, 0, 1, 0, True),
        (0, 0, 0, 1, True),
    ],
)
def test__create_sample(
    monkeypatch, num_hosts, num_hosts_excluded, num_services, num_services_excluded, returns_sample
):
    def _mock_livestatus(query):
        if "GET hosts" in query:
            return num_hosts, num_hosts_excluded
        return num_services, num_services_excluded

    monkeypatch.setattr(
        license_usage,
        "_get_stats_from_livestatus",
        _mock_livestatus,
    )

    monkeypatch.setattr(
        license_usage,
        "load_extensions",
        lambda: LicenseUsageExtensions(ntop=False),
    )

    sample = license_usage._create_sample()
    if returns_sample:
        assert sample is not None
    else:
        assert sample is None

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import pathlib

import pytest

from cmk.plugins.kube import performance
from cmk.server_side_programs.v1_unstable import Storage
from tests.cmk.plugins.kube.agent_kube import factory

CONTAINER_STORE_KEY = "store"


@pytest.fixture(name="storage")
def fixture_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> Storage:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))
    return Storage("agent_kube", "server_name")


def _cpu_sample(
    container_name: str = "bernd", timestamp: float = 1.0, value: str = "10.0"
) -> performance.CPUSample:
    sample: performance.CPUSample = factory.CPUSampleFactory.build(
        container_name=container_name,
        timestamp=timestamp,
        metric_value_string=value,
    )
    return sample


def test_create_cpu_rate_samples(storage: Storage) -> None:
    first = performance.create_cpu_rate_samples(
        storage, CONTAINER_STORE_KEY, [_cpu_sample(timestamp=1.0, value="10.0")], 10.0
    )
    second = performance.create_cpu_rate_samples(
        storage, CONTAINER_STORE_KEY, [_cpu_sample(timestamp=2.0, value="40.0")], 70.0
    )

    assert list(first) == []  # a single sample is not enough to compute a rate
    assert [s.rate for s in second] == [30.0]


def test_create_cpu_rate_samples_reuses_rate_for_unchanged_sample(storage: Storage) -> None:
    """The cluster collector returns unchanged samples while its data is not updated.

    No rate can be computed from an unchanged sample, so the previously computed one is
    reused. Otherwise the container would vanish from the performance sections.
    """
    performance.create_cpu_rate_samples(
        storage, CONTAINER_STORE_KEY, [_cpu_sample(timestamp=1.0, value="10.0")], 10.0
    )
    fresh = performance.create_cpu_rate_samples(
        storage, CONTAINER_STORE_KEY, [_cpu_sample(timestamp=2.0, value="40.0")], 70.0
    )
    reused = performance.create_cpu_rate_samples(
        storage, CONTAINER_STORE_KEY, [_cpu_sample(timestamp=2.0, value="40.0")], 130.0
    )

    assert list(reused) == list(fresh)


def test_create_cpu_rate_samples_reuse_does_not_extend_validity(storage: Storage) -> None:
    """A rate stays reusable until it expires, no matter how often it was reused before.

    Reusing must not reset the age of a rate, otherwise a stalled collector would never
    surface.
    """
    performance.create_cpu_rate_samples(
        storage, CONTAINER_STORE_KEY, [_cpu_sample(timestamp=1.0, value="10.0")], 10.0
    )
    performance.create_cpu_rate_samples(
        storage, CONTAINER_STORE_KEY, [_cpu_sample(timestamp=2.0, value="40.0")], 70.0
    )
    unchanged_sample = [_cpu_sample(timestamp=2.0, value="40.0")]

    reused = performance.create_cpu_rate_samples(
        storage, CONTAINER_STORE_KEY, unchanged_sample, 130.0
    )
    reused_again = performance.create_cpu_rate_samples(
        storage,
        CONTAINER_STORE_KEY,
        unchanged_sample,
        70.0 + performance.PREVIOUS_RATE_VALIDITY_SECS - 1.0,
    )
    expired = performance.create_cpu_rate_samples(
        storage,
        CONTAINER_STORE_KEY,
        unchanged_sample,
        70.0 + performance.PREVIOUS_RATE_VALIDITY_SECS + 1.0,
    )

    assert len(reused) == 1
    assert list(reused_again) == list(reused)
    assert list(expired) == []


def test_create_cpu_rate_samples_keeps_containers_with_unchanged_samples(storage: Storage) -> None:
    """Node collectors push independently, so a single poll can mix fresh and unchanged samples."""
    performance.create_cpu_rate_samples(
        storage,
        CONTAINER_STORE_KEY,
        [
            _cpu_sample("fresh-node", timestamp=1.0, value="10.0"),
            _cpu_sample("stale-node", timestamp=1.0, value="100.0"),
        ],
        10.0,
    )
    performance.create_cpu_rate_samples(
        storage,
        CONTAINER_STORE_KEY,
        [
            _cpu_sample("fresh-node", timestamp=2.0, value="40.0"),
            _cpu_sample("stale-node", timestamp=2.0, value="220.0"),
        ],
        70.0,
    )
    samples = performance.create_cpu_rate_samples(
        storage,
        CONTAINER_STORE_KEY,
        [
            _cpu_sample("fresh-node", timestamp=3.0, value="70.0"),
            _cpu_sample("stale-node", timestamp=2.0, value="220.0"),
        ],
        130.0,
    )

    assert sorted(s.rate for s in samples) == [30.0, 120.0]


def test_create_cpu_rate_samples_reads_store_without_rates(storage: Storage) -> None:
    """Stores written before the rates were persisted must still be readable."""
    storage.write(
        CONTAINER_STORE_KEY,
        json.dumps({"cpu": [_cpu_sample(timestamp=1.0, value="10.0").model_dump(mode="json")]}),
    )

    samples = performance.create_cpu_rate_samples(
        storage, CONTAINER_STORE_KEY, [_cpu_sample(timestamp=2.0, value="40.0")], 70.0
    )

    assert [s.rate for s in samples] == [30.0]

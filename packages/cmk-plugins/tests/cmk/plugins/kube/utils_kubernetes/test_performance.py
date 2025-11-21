#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pathlib

import pytest

from cmk.plugins.kube import performance
from cmk.server_side_programs.v1_unstable import Storage
from tests.cmk.plugins.kube.agent_kube import factory


def test__create_cpu_rate_metrics(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))
    container_store_key = "store"
    first_cpu_sample = factory.CPUSampleFactory.build(timestamp=1.0, container_name="bernd")
    second_cpu_sample = factory.CPUSampleFactory.build(timestamp=2.0, container_name="bernd")
    storage = Storage("agent_kube", "server_name")
    performance.create_cpu_rate_metrics(storage, container_store_key, [first_cpu_sample])
    samples = performance.create_cpu_rate_metrics(storage, container_store_key, [second_cpu_sample])
    assert len(samples) == 1

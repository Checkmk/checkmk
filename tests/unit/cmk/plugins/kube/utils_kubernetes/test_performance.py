#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pathlib

from cmk.plugins.kube import performance

from tests.unit.cmk.plugins.kube.agent_kube import factory


def test__create_cpu_rate_metrics(tmp_path: pathlib.Path) -> None:
    container_store_file = tmp_path.joinpath("store.json")
    first_cpu_sample = factory.CPUSampleFactory.build(timestamp=1.0, container_name="bernd")
    second_cpu_sample = factory.CPUSampleFactory.build(timestamp=2.0, container_name="bernd")
    performance._create_cpu_rate_metrics(container_store_file, [first_cpu_sample])
    samples = performance._create_cpu_rate_metrics(container_store_file, [second_cpu_sample])
    assert len(samples) == 1

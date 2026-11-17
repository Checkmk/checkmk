#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Write a suite's benchmark.json where perftest_upload.sh collects it.

The nightly Bazel performance job stores a suite's timings from that file. Under
``bazel test`` it has to be in the suite's test outputs, next to the resource files of
:mod:`tests.performance.sysmon`. A suite loads this plugin with
``-p tests.performance.benchmark_json`` in its ``args``.

Each benchmark in the file also gets its test's docstring as ``description``, which the
upload stores with the scenario; an empty one clears the stored description.
"""

import inspect
import os
from pathlib import Path

import pytest

_DESCRIPTIONS = pytest.StashKey[dict[str, str]]()


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    if (outputs_dir := os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")) is None:
        return
    if config.option.benchmark_json is None:
        config.option.benchmark_json = Path(outputs_dir) / "benchmark.json"


def pytest_collection_finish(session: pytest.Session) -> None:
    session.config.stash[_DESCRIPTIONS] = {
        item.nodeid: inspect.getdoc(item.obj) or ""
        for item in session.items
        if isinstance(item, pytest.Function)
    }


def pytest_benchmark_update_json(config: pytest.Config, output_json: dict[str, object]) -> None:
    descriptions = config.stash.get(_DESCRIPTIONS, {})
    assert isinstance(benchmark_entries := output_json["benchmarks"], list)
    for benchmark in benchmark_entries:
        benchmark["description"] = descriptions.get(benchmark["fullname"], "")

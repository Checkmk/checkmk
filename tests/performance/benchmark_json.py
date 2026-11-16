#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Write a suite's benchmark.json where perftest_upload.sh collects it.

The nightly Bazel performance job stores a suite's timings from that file. Under
``bazel test`` it has to be in the suite's test outputs, next to the resource files of
:mod:`tests.performance.sysmon`. A suite loads this plugin with
``-p tests.performance.benchmark_json`` in its ``args``.
"""

import os
from pathlib import Path

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    if (outputs_dir := os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")) is None:
        return
    if config.option.benchmark_json is None:
        config.option.benchmark_json = Path(outputs_dir) / "benchmark.json"

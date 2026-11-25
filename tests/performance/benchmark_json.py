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

A suite that sets the file itself hands it over as :class:`JsonFile`.
"""

import inspect
import os
from pathlib import Path
from types import TracebackType
from typing import BinaryIO

import pytest

_DESCRIPTIONS = pytest.StashKey[dict[str, str]]()


class JsonFile:
    """``--benchmark-json`` as pytest-benchmark 5.2 takes it, opened only once it writes.

    It declares the option as ``argparse.FileType("wb")`` and writes with ``with option as
    fh``, so a path set in its place fails when the session ends and no benchmark.json is
    written. An open file would empty an earlier run's benchmark.json right away, though
    nothing replaces it if no benchmark runs, e.g. with ``--collect-only``. This opens the
    file only when pytest-benchmark writes it.
    """

    def __init__(self, path: Path) -> None:
        self.name = str(path)
        self._file: BinaryIO | None = None

    def __enter__(self) -> BinaryIO:
        self._file = open(self.name, "wb")  # pylint: disable=consider-using-with
        return self._file

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def __str__(self) -> str:
        return self.name


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    if (outputs_dir := os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")) is None:
        return
    if config.option.benchmark_json is None:
        config.option.benchmark_json = JsonFile(Path(outputs_dir) / "benchmark.json")


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

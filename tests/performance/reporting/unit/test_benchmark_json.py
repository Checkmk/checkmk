#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

import pytest

from tests.performance.benchmark_json import (
    pytest_benchmark_update_json,
    pytest_collection_finish,
)

REPO = str(Path(__file__).resolve().parents[4])


def _documented() -> None:
    """Measures nothing much."""


def _undocumented() -> None:
    pass


@pytest.mark.parametrize(
    "test_function, description",
    [
        pytest.param(_documented, "Measures nothing much.", id="docstring"),
        pytest.param(_undocumented, "", id="no-docstring"),
    ],
)
def test_a_benchmark_gets_its_tests_docstring_as_description(
    test_function: Callable[[], None], description: str
) -> None:
    config = Mock(spec=pytest.Config, stash=pytest.Stash())
    item = Mock(spec=pytest.Function, nodeid="test_scenarios.py::test_x", obj=test_function)
    session = Mock(spec=pytest.Session, config=config, items=[item])
    output_json: dict[str, object] = {"benchmarks": [{"fullname": "test_scenarios.py::test_x"}]}

    pytest_collection_finish(session)
    pytest_benchmark_update_json(config, output_json)

    assert output_json["benchmarks"] == [
        {"fullname": "test_scenarios.py::test_x", "description": description}
    ]


def _run_suite_under_bazel(tmp_path: Path, *args: str) -> Path:
    """Run a one-benchmark suite with the plugin as `bazel test` would; return its outputs."""
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "test_scenario.py").write_text(
        'def test_x(benchmark):\n    """Measures nothing much."""\n    benchmark(lambda: None)\n'
    )
    (suite / "pytest.ini").write_text("[pytest]\n")
    outputs = tmp_path / "outputs"
    outputs.mkdir(exist_ok=True)

    # Run from the repository, as its "tests" comes first on sys.path only from there: the venv
    # puts the packages, some of them with a "tests" of their own, ahead of PYTHONPATH. The
    # suite's own ini keeps the repository's pytest configuration out.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "tests.performance.benchmark_json"]
        + ["-p", "no:cacheprovider", "-c", str(suite / "pytest.ini"), *args, str(suite)],
        env=os.environ | {"TEST_UNDECLARED_OUTPUTS_DIR": str(outputs)},
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    return outputs


def test_a_suite_under_bazel_writes_its_benchmark_json(tmp_path: Path) -> None:
    """Under `bazel test`, the plugin points --benchmark-json into the test outputs.

    Runs a real session, so it fails if the installed pytest-benchmark cannot write to what
    the plugin hands it."""
    outputs = _run_suite_under_bazel(tmp_path)

    benchmarks = json.loads((outputs / "benchmark.json").read_text())["benchmarks"]
    assert [b["description"] for b in benchmarks] == ["Measures nothing much."]


def test_a_session_without_benchmarks_keeps_the_earlier_benchmark_json(tmp_path: Path) -> None:
    """The file is opened only when pytest-benchmark writes it, so an earlier run's stays."""
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "benchmark.json").write_text('{"benchmarks": []}')

    outputs = _run_suite_under_bazel(tmp_path, "--collect-only")

    assert (outputs / "benchmark.json").read_text() == '{"benchmarks": []}'

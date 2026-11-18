#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from unittest.mock import Mock

import pytest

from tests.performance.benchmark_json import (
    pytest_benchmark_update_json,
    pytest_collection_finish,
)


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

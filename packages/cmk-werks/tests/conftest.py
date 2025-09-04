#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test configuration for pytest-recording."""

from pathlib import Path
from typing import Any

import pytest

# Avoid collecting files literally named 'sitecustomize.py' to prevent
# import collisions with the interpreter's auto-loaded sitecustomize.
collect_ignore_glob = ["sitecustomize.py"]


@pytest.fixture(scope="module")
def vcr_config(request: pytest.FixtureRequest) -> dict[str, Any]:  # noqa: ARG001
    """Configure VCR cassettes for pytest-recording."""
    return {
        "filter_headers": [
            ("authorization", "REDACTED"),
            ("x-api-key", "REDACTED"),
            ("api-key", "REDACTED"),
            ("openai-api-key", "REDACTED"),
        ],
        "filter_query_parameters": [
            ("api_key", "REDACTED"),
            ("key", "REDACTED"),
        ],
        "filter_post_data_parameters": [
            ("api_key", "REDACTED"),
            ("key", "REDACTED"),
        ],
        "decode_compressed_response": True,
        "record_mode": "once",
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "ignore_localhost": False,
    }


@pytest.fixture(scope="module")
def vcr_cassette_dir(request: pytest.FixtureRequest) -> str:
    """Set cassette directory based on test file name."""
    test_file = Path(request.module.__file__).stem
    # Get the current test directory and use cassettes subdirectory
    test_dir = Path(request.module.__file__).parent
    cassette_dir = test_dir / "cassettes" / f"{test_file}_cassettes"
    cassette_dir.mkdir(parents=True, exist_ok=True)
    return str(cassette_dir)


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "block_network: block network access during test execution")


@pytest.fixture(autouse=True)
def auto_block_network(request: pytest.FixtureRequest) -> None:
    """Automatically apply block_network marker to all tests."""
    request.node.add_marker(pytest.mark.block_network)

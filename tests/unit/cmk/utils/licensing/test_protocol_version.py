#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest

from cmk.ccc.version import Edition

from cmk.utils.licensing.protocol_version import get_licensing_protocol_version


@pytest.fixture
def edition_fn_mock() -> Generator[Mock]:
    with patch("cmk.utils.licensing.protocol_version.edition") as edition_fn_mock:
        yield edition_fn_mock


@pytest.mark.parametrize(
    "edition, expected_version",
    [
        pytest.param(Edition.CSE, "3.1"),
        pytest.param(Edition.CEE, "3.1"),
        pytest.param(Edition.CCE, "3.1"),
        pytest.param(Edition.CME, "3.1"),
        pytest.param(Edition.CRE, "3.1"),
    ],
)
def test_get_licensing_protocol_version(
    edition_fn_mock: Mock, edition: Edition, expected_version: str
) -> None:
    """Test that get_licensing_protocol_version returns the correct version for different editions."""
    edition_fn_mock.return_value = edition
    assert get_licensing_protocol_version() == expected_version

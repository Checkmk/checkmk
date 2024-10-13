#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.semantic_version import SemanticVersion


@pytest.mark.parametrize(
    "raw_version",
    [
        pytest.param("2.0.1", id="perfectly matched version"),
        pytest.param("2.0.1.3", id="micro versions dropped"),
        pytest.param("2.0.1-rc3", id="release candidates dropped"),
        pytest.param("gerrit-2.0.1.war", id="from release filename"),
    ],
)
def test_semantic_version_from_string(raw_version: str) -> None:
    value = SemanticVersion.from_string(raw_version)
    expected = SemanticVersion(major=2, minor=0, patch=1)
    assert value == expected


@pytest.mark.parametrize(
    "raw_version",
    [
        pytest.param("", id="blank string"),
        pytest.param("2.0", id="missing patch version"),
        pytest.param("2-0-1", id="hyphen delimeter not supported"),
        pytest.param("major.minor.patch", id="only digits matched with correct pattern"),
    ],
)
def test_semantic_version_from_string_raises(raw_version: str) -> None:
    with pytest.raises(ValueError):
        SemanticVersion.from_string(raw_version)
